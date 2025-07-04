import pygame
from pygame.locals import *
import moderngl
import numpy as np
from pyrr import Matrix44, Vector3
import sys

# === CONFIG ===
ROOM_SIZE = 10
WALL_COLORS = {
    "floor": (0.2, 0.2, 0.2),
    "ceiling": (0.4, 0.4, 0.4),
    "north": (1.0, 0.0, 0.0),
    "south": (0.0, 1.0, 0.0),
    "east":  (0.0, 0.0, 1.0),
    "west":  (1.0, 1.0, 0.0),
}
MOUSE_SENSITIVITY = 0.1
MOVE_SPEED = 0.1
JUMP_FORCE = 0.2
GRAVITY = -0.01

# === SHADERS ===
VERTEX_SHADER = '''
#version 330
in vec3 in_position;
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
void main() {
    gl_Position = projection * view * model * vec4(in_position, 1.0);
}
'''

FRAGMENT_SHADER = '''
#version 330
uniform vec3 color;
out vec4 fragColor;
void main() {
    fragColor = vec4(color, 1.0);
}
'''

# === CAMERA CLASS ===
class Camera:
    def __init__(self, position):
        self.position = Vector3(position)
        self.pitch = 0.0
        self.yaw = -90.0
        self.velocity = Vector3([0, 0, 0])
        self.on_ground = True

    def get_view_matrix(self):
        front = self.get_front_vector()
        center = self.position + front
        up = Vector3([0, 1, 0])
        return Matrix44.look_at(self.position, center, up)

    def get_front_vector(self):
        rad_pitch = np.radians(self.pitch)
        rad_yaw = np.radians(self.yaw)
        x = np.cos(rad_pitch) * np.cos(rad_yaw)
        y = np.sin(rad_pitch)
        z = np.cos(rad_pitch) * np.sin(rad_yaw)
        return Vector3([x, y, z]).normalized

    def move(self, direction):
        front = self.get_front_vector()
        right = Vector3(np.cross(front, [0, 1, 0])).normalized
        if direction == "forward":
            self.position += front * MOVE_SPEED
        elif direction == "backward":
            self.position -= front * MOVE_SPEED
        elif direction == "left":
            self.position -= right * MOVE_SPEED
        elif direction == "right":
            self.position += right * MOVE_SPEED

    def apply_gravity(self):
        self.velocity.y += GRAVITY
        self.position.y += self.velocity.y
        if self.position.y < 1.0:
            self.position.y = 1.0
            self.velocity.y = 0
            self.on_ground = True

    def jump(self):
        if self.on_ground:
            self.velocity.y += JUMP_FORCE
            self.on_ground = False

    def look(self, dx, dy):
        self.yaw += dx * MOUSE_SENSITIVITY
        self.pitch -= dy * MOUSE_SENSITIVITY
        self.pitch = np.clip(self.pitch, -89.0, 89.0)

# === MAIN FUNCTION ===
def main():
    pygame.init()
    pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)

    ctx = moderngl.create_context()
    prog = ctx.program(vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER)
    vbo = ctx.buffer(np.array([
        # Plane (quad) positions for each wall
        # Floor
        -ROOM_SIZE, 0, -ROOM_SIZE,  ROOM_SIZE, 0, -ROOM_SIZE,
         ROOM_SIZE, 0,  ROOM_SIZE, -ROOM_SIZE, 0,  ROOM_SIZE,
        # Ceiling
        -ROOM_SIZE, ROOM_SIZE * 2, -ROOM_SIZE,  ROOM_SIZE, ROOM_SIZE * 2, -ROOM_SIZE,
         ROOM_SIZE, ROOM_SIZE * 2,  ROOM_SIZE, -ROOM_SIZE, ROOM_SIZE * 2,  ROOM_SIZE,
    ], dtype='f4').tobytes())

    vao = ctx.simple_vertex_array(prog, vbo, 'in_position')
    camera = Camera([0.0, 1.0, 5.0])

    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT or (
                event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_SPACE:
                    camera.jump()
            elif event.type == MOUSEMOTION:
                dx, dy = event.rel
                camera.look(dx, dy)

        keys = pygame.key.get_pressed()
        if keys[K_w]: camera.move("forward")
        if keys[K_s]: camera.move("backward")
        if keys[K_a]: camera.move("left")
        if keys[K_d]: camera.move("right")

        camera.apply_gravity()

        ctx.clear(0.1, 0.1, 0.1)
        proj = Matrix44.perspective_projection(70.0, 800/600, 0.1, 100.0)
        view = camera.get_view_matrix()

        # Draw all 6 walls with different colors
        def draw_wall(model_matrix, color):
            prog['model'].write(model_matrix.astype('f4').tobytes())
            prog['view'].write(view.astype('f4').tobytes())
            prog['projection'].write(proj.astype('f4').tobytes())
            prog['color'].value = color
            vao.render(moderngl.TRIANGLE_FAN)

        # Floor
        model = Matrix44.identity()
        draw_wall(model, WALL_COLORS['floor'])

        # Ceiling
        model = Matrix44.from_translation([0, ROOM_SIZE * 2, 0])
        draw_wall(model, WALL_COLORS['ceiling'])

        # North wall (z = -ROOM_SIZE)
        model = Matrix44.from_eulers([np.pi/2, 0, 0]) @ Matrix44.from_translation([0, ROOM_SIZE, -ROOM_SIZE])
        draw_wall(model, WALL_COLORS['north'])

        # South wall (z = ROOM_SIZE)
        model = Matrix44.from_eulers([-np.pi/2, 0, 0]) @ Matrix44.from_translation([0, ROOM_SIZE, ROOM_SIZE])
        draw_wall(model, WALL_COLORS['south'])

        # East wall (x = ROOM_SIZE)
        model = Matrix44.from_eulers([0, 0, -np.pi/2]) @ Matrix44.from_translation([ROOM_SIZE, ROOM_SIZE, 0])
        draw_wall(model, WALL_COLORS['east'])

        # West wall (x = -ROOM_SIZE)
        model = Matrix44.from_eulers([0, 0, np.pi/2]) @ Matrix44.from_translation([-ROOM_SIZE, ROOM_SIZE, 0])
        draw_wall(model, WALL_COLORS['west'])

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()

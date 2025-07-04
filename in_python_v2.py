import pygame
import pygame.gfxdraw
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import sys
import numpy as np

class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z
    
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def normalize(self):
        length = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length > 0:
            return Vector3(self.x / length, self.y / length, self.z / length)
        return Vector3(0, 0, 0)
    
    def cross(self, other):
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

class Camera:
    def __init__(self):
        self.position = Vector3(0, 1.7, 0)
        self.pitch = 0
        self.yaw = 0
        self.sensitivity = 0.002
        
    def update_rotation(self, mouse_x, mouse_y):
        self.yaw -= mouse_x * self.sensitivity
        self.pitch -= mouse_y * self.sensitivity
        
        # Clamp pitch to prevent flipping
        self.pitch = max(-math.pi/2, min(math.pi/2, self.pitch))
    
    def get_forward_vector(self):
        return Vector3(
            math.sin(self.yaw) * math.cos(self.pitch),
            math.sin(self.pitch),
            -math.cos(self.yaw) * math.cos(self.pitch)
        )
    
    def get_right_vector(self):
        forward = self.get_forward_vector()
        up = Vector3(0, 1, 0)
        return forward.cross(up).normalize()
    
    def apply_view_matrix(self):
        glRotatef(math.degrees(-self.pitch), 1, 0, 0)
        glRotatef(math.degrees(-self.yaw), 0, 1, 0)
        glTranslatef(-self.position.x, -self.position.y, -self.position.z)

class RoomSimulator:
    def __init__(self):
        # Configuration
        self.config = {
            'move_speed': 8,
            'mouse_sensitivity': 2,
            'jump_height': 6,
            'gravity': -20,
            'player_height': 1.7,
            'player_radius': 0.4,
            'room_size': {'width': 15, 'height': 6, 'depth': 15},
            'colors': {
                'walls': {
                    'front': [1.0, 1.0, 1.0],
                    'back': [1.0, 1.0, 1.0],
                    'left': [1.0, 1.0, 1.0],
                    'right': [1.0, 1.0, 1.0]
                },
                'floor': [0.5, 0.5, 0.5],
                'ceiling': [0.87, 0.87, 0.87],
                'furniture': {
                    'table': [0.55, 0.27, 0.075],
                    'chair': [0.63, 0.32, 0.18],
                    'bed': [0.28, 0.51, 0.71]
                }
            },
            'lighting': {
                'ambient': 0.4,
                'sun_intensity': 0.8,
                'sun_position': [5, 10, 5],
                'room_light': 0.6
            }
        }
        
        self.camera = Camera()
        self.velocity = Vector3(0, 0, 0)
        self.move_direction = {
            'forward': False,
            'backward': False,
            'left': False,
            'right': False
        }
        self.is_jumping = False
        self.is_on_floor = False
        self.walls = []
        self.mouse_locked = False
        self.clock = pygame.time.Clock()
        # self.keys = pygame.key.get_pressed()  # ❌ Removed this line
        
        # Initialize pygame and OpenGL
        pygame.init()
        pygame.display.set_mode((1200, 800), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Room Simulator - Python")
        
        # Set up OpenGL
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Set up projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, 1200/800, 0.1, 1000)
        glMatrixMode(GL_MODELVIEW)
        
        # Set up lighting
        self.setup_lighting()
        
        # Create room and furniture
        self.create_room()
        self.create_furniture()
        
        # Show instructions
        print("=== 3D Room Simulator ===")
        print("Controls:")
        print("WASD: Move")
        print("Space: Jump")
        print("Mouse: Look around")
        print("Click to lock mouse cursor")
        print("ESC: Exit")
        print("F: Toggle fullscreen")
        print("R: Reset position")
        print("1-4: Change wall colors")
        print("5-6: Adjust lighting")
        print("========================")
    
    def setup_lighting(self):
        # Ambient light
        glLightfv(GL_LIGHT0, GL_AMBIENT, [
            self.config['lighting']['ambient'],
            self.config['lighting']['ambient'],
            self.config['lighting']['ambient'],
            1.0
        ])
        
        # Directional light (sun)
        glLightfv(GL_LIGHT0, GL_POSITION, 
                  self.config['lighting']['sun_position'] + [0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [
            self.config['lighting']['sun_intensity'],
            self.config['lighting']['sun_intensity'],
            self.config['lighting']['sun_intensity'],
            1.0
        ])
        
        # Enable lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
    
    def create_room(self):
        w, h, d = (self.config['room_size']['width'], 
                  self.config['room_size']['height'], 
                  self.config['room_size']['depth'])
        
        # Add wall colliders
        self.walls = [
            # Front wall
            {'pos': Vector3(0, 0, d/2), 'size': Vector3(w, h, 0.2), 'rotation': 0},
            # Back wall
            {'pos': Vector3(0, 0, -d/2), 'size': Vector3(w, h, 0.2), 'rotation': 0},
            # Left wall
            {'pos': Vector3(-w/2, 0, 0), 'size': Vector3(0.2, h, d), 'rotation': 0},
            # Right wall
            {'pos': Vector3(w/2, 0, 0), 'size': Vector3(0.2, h, d), 'rotation': 0}
        ]
    
    def create_furniture(self):
        # Table
        self.walls.append({
            'pos': Vector3(0, 0, -4),
            'size': Vector3(3, 0.6, 1.5),
            'rotation': 0
        })
        
        # Chairs
        self.walls.append({
            'pos': Vector3(-1, 0, -2.5),
            'size': Vector3(0.6, 1.2, 0.6),
            'rotation': 0
        })
        self.walls.append({
            'pos': Vector3(1, 0, -2.5),
            'size': Vector3(0.6, 1.2, 0.6),
            'rotation': 0
        })
        
        # Bed
        self.walls.append({
            'pos': Vector3(-4, 0, 4),
            'size': Vector3(4, 0.6, 2.5),
            'rotation': 0
        })
        
        # Bookshelf
        self.walls.append({
            'pos': Vector3(6, 0, 0),
            'size': Vector3(0.4, 4, 3),
            'rotation': 0
        })
    
    def draw_cube(self, pos, size, color):
        glColor3f(*color)
        glPushMatrix()
        glTranslatef(pos.x, pos.y + size.y/2, pos.z)
        glScalef(size.x, size.y, size.z)
        
        # Draw cube faces
        glBegin(GL_QUADS)
        
        # Front face
        glNormal3f(0, 0, 1)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        
        # Back face
        glNormal3f(0, 0, -1)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        
        # Top face
        glNormal3f(0, 1, 0)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, -0.5)
        
        # Bottom face
        glNormal3f(0, -1, 0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        
        # Right face
        glNormal3f(1, 0, 0)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        
        # Left face
        glNormal3f(-1, 0, 0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        
        glEnd()
        glPopMatrix()
    
    def draw_plane(self, pos, size, color, normal):
        glColor3f(*color)
        glPushMatrix()
        glTranslatef(pos.x, pos.y, pos.z)
        
        # Set normal
        glNormal3f(normal.x, normal.y, normal.z)
        
        glBegin(GL_QUADS)
        glVertex3f(-size.x/2, 0, -size.z/2)
        glVertex3f(size.x/2, 0, -size.z/2)
        glVertex3f(size.x/2, 0, size.z/2)
        glVertex3f(-size.x/2, 0, size.z/2)
        glEnd()
        
        glPopMatrix()
    
    def draw_wall(self, pos, size, color, rotation=0):
        glColor3f(*color)
        glPushMatrix()
        glTranslatef(pos.x, pos.y + size.y/2, pos.z)
        glRotatef(math.degrees(rotation), 0, 1, 0)
        
        # Determine which direction the wall faces
        if abs(size.x) > abs(size.z):  # Wall along X axis
            glNormal3f(0, 0, 1)
            glBegin(GL_QUADS)
            glVertex3f(-size.x/2, -size.y/2, 0)
            glVertex3f(size.x/2, -size.y/2, 0)
            glVertex3f(size.x/2, size.y/2, 0)
            glVertex3f(-size.x/2, size.y/2, 0)
            glEnd()
        else:  # Wall along Z axis
            glNormal3f(1, 0, 0)
            glBegin(GL_QUADS)
            glVertex3f(0, -size.y/2, -size.z/2)
            glVertex3f(0, -size.y/2, size.z/2)
            glVertex3f(0, size.y/2, size.z/2)
            glVertex3f(0, size.y/2, -size.z/2)
            glEnd()
        
        glPopMatrix()
    
    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Apply camera
        self.camera.apply_view_matrix()
        
        # Draw room
        w, h, d = (self.config['room_size']['width'], 
                  self.config['room_size']['height'], 
                  self.config['room_size']['depth'])
        
        # Floor
        self.draw_plane(Vector3(0, 0, 0), Vector3(w, 0, d), 
                       self.config['colors']['floor'], Vector3(0, 1, 0))
        
        # Ceiling
        self.draw_plane(Vector3(0, h, 0), Vector3(w, 0, d), 
                       self.config['colors']['ceiling'], Vector3(0, -1, 0))
        
        # Walls
        wall_colors = self.config['colors']['walls']
        self.draw_wall(Vector3(0, 0, d/2), Vector3(w, h, 0.2), wall_colors['front'])
        self.draw_wall(Vector3(0, 0, -d/2), Vector3(w, h, 0.2), wall_colors['back'])
        self.draw_wall(Vector3(-w/2, 0, 0), Vector3(0.2, h, d), wall_colors['left'])
        self.draw_wall(Vector3(w/2, 0, 0), Vector3(0.2, h, d), wall_colors['right'])
        
        # Furniture
        furniture_colors = self.config['colors']['furniture']
        
        # Table
        self.draw_cube(Vector3(0, 0, -4), Vector3(3, 0.6, 1.5), furniture_colors['table'])
        
        # Chairs
        self.draw_cube(Vector3(-1, 0, -2.5), Vector3(0.6, 1.2, 0.6), furniture_colors['chair'])
        self.draw_cube(Vector3(1, 0, -2.5), Vector3(0.6, 1.2, 0.6), furniture_colors['chair'])
        
        # Bed
        self.draw_cube(Vector3(-4, 0, 4), Vector3(4, 0.6, 2.5), furniture_colors['bed'])
        
        # Bookshelf
        self.draw_cube(Vector3(6, 0, 0), Vector3(0.4, 4, 3), [0.55, 0.27, 0.075])
        
        pygame.display.flip()
    
    def check_collision(self, new_pos):
        for wall in self.walls:
            # Simple AABB collision detection
            wall_min = Vector3(
                wall['pos'].x - wall['size'].x/2,
                wall['pos'].y,
                wall['pos'].z - wall['size'].z/2
            )
            wall_max = Vector3(
                wall['pos'].x + wall['size'].x/2,
                wall['pos'].y + wall['size'].y,
                wall['pos'].z + wall['size'].z/2
            )
            
            player_min = Vector3(
                new_pos.x - self.config['player_radius'],
                new_pos.y - self.config['player_height'],
                new_pos.z - self.config['player_radius']
            )
            player_max = Vector3(
                new_pos.x + self.config['player_radius'],
                new_pos.y,
                new_pos.z + self.config['player_radius']
            )
            
            if (player_min.x < wall_max.x and player_max.x > wall_min.x and
                player_min.y < wall_max.y and player_max.y > wall_min.y and
                player_min.z < wall_max.z and player_max.z > wall_min.z):
                return True
        return False
    
    def update_movement(self, dt):
        if not self.mouse_locked:
            return
        
        # Get movement vectors
        forward = self.camera.get_forward_vector()
        right = self.camera.get_right_vector()
        
        # Reset horizontal velocity
        self.velocity.x = 0
        self.velocity.z = 0
        
        # Apply movement
        speed = self.config['move_speed']
        if self.move_direction['forward']:
            self.velocity.x += forward.x * speed
            self.velocity.z += forward.z * speed
        if self.move_direction['backward']:
            self.velocity.x -= forward.x * speed
            self.velocity.z -= forward.z * speed
        if self.move_direction['left']:
            self.velocity.x -= right.x * speed
            self.velocity.z -= right.z * speed
        if self.move_direction['right']:
            self.velocity.x += right.x * speed
            self.velocity.z += right.z * speed
        
        # Apply gravity
        self.velocity.y += self.config['gravity'] * dt
        
        # Calculate new position
        old_pos = Vector3(self.camera.position.x, self.camera.position.y, self.camera.position.z)
        new_pos = Vector3(
            old_pos.x + self.velocity.x * dt,
            old_pos.y + self.velocity.y * dt,
            old_pos.z + self.velocity.z * dt
        )
        
        # Check collision and update position
        if not self.check_collision(new_pos):
            self.camera.position = new_pos
        else:
            # Try sliding along walls
            new_x_pos = Vector3(old_pos.x + self.velocity.x * dt, new_pos.y, old_pos.z)
            if not self.check_collision(new_x_pos):
                self.camera.position.x = new_x_pos.x
            
            new_z_pos = Vector3(old_pos.x, new_pos.y, old_pos.z + self.velocity.z * dt)
            if not self.check_collision(new_z_pos):
                self.camera.position.z = new_z_pos.z
        
        # Floor collision
        if self.camera.position.y <= self.config['player_height']:
            self.camera.position.y = self.config['player_height']
            self.velocity.y = 0
            self.is_jumping = False
            self.is_on_floor = True
        
        # Ceiling collision
        if self.camera.position.y >= self.config['room_size']['height'] - 0.1:
            self.camera.position.y = self.config['room_size']['height'] - 0.1
            self.velocity.y = 0
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_r:
                    # Reset position
                    self.camera.position = Vector3(0, 1.7, 0)
                    self.camera.pitch = 0
                    self.camera.yaw = 0
                    self.velocity = Vector3(0, 0, 0)
                elif event.key == pygame.K_SPACE:
                    if not self.is_jumping and self.is_on_floor:
                        self.velocity.y = self.config['jump_height']
                        self.is_jumping = True
                        self.is_on_floor = False
                # Color changing keys
                elif event.key == pygame.K_1:
                    self.config['colors']['walls']['front'] = [1.0, 0.0, 0.0]
                elif event.key == pygame.K_2:
                    self.config['colors']['walls']['back'] = [0.0, 1.0, 0.0]
                elif event.key == pygame.K_3:
                    self.config['colors']['walls']['left'] = [0.0, 0.0, 1.0]
                elif event.key == pygame.K_4:
                    self.config['colors']['walls']['right'] = [1.0, 1.0, 0.0]
                elif event.key == pygame.K_5:
                    self.config['lighting']['ambient'] = min(1.0, self.config['lighting']['ambient'] + 0.1)
                    self.setup_lighting()
                elif event.key == pygame.K_6:
                    self.config['lighting']['ambient'] = max(0.0, self.config['lighting']['ambient'] - 0.1)
                    self.setup_lighting()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_locked = True
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
            
            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_locked:
                    self.camera.update_rotation(event.rel[0] * self.config['mouse_sensitivity'], 
                                              event.rel[1] * self.config['mouse_sensitivity'])
        
        # Handle continuous key presses
        keys = pygame.key.get_pressed()
        self.move_direction['forward'] = keys[pygame.K_w]
        self.move_direction['backward'] = keys[pygame.K_s]
        self.move_direction['left'] = keys[pygame.K_a]
        self.move_direction['right'] = keys[pygame.K_d]
        
        return True
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0  # Convert to seconds
            
            running = self.handle_events()
            self.update_movement(dt)
            self.render()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        simulator = RoomSimulator()
        simulator.run()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()

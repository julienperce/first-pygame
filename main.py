import os

import arcade
from arcade import Texture
from arcade.gui import *
from arcade.gui.ui_style import UIStyle

import pyglet
from pyglet.event import EventDispatcher

import time
import sys
import random
from typing import Optional
# WINDOW DIMENSION CONSTANTS
# 21:9 aspect ratio, 720p
SCREEN_WIDTH = 1680
SCREEN_HEIGHT = 720
SCREEN_TITLE = "the clock is ticking..."
MUSIC_VOLUME = 0.005
FX_VOLUME = 0.015

# PLAYER CONSTANTS
PLAYER_MOVEMENT_SPEED = 5 # Movement speed is measured in pixels per frame
PLAYER_JUMP_SPEED = 20

# PHYSICS CONSANTS
GRAVITY = 1

# SIDESCROLLING MECHANIC CONSTANTS
"""
    Default values for sidescroll : 250, 250, 50, 100
    Default values for camera follow: 840, 840, 100, 620
"""
# The minimum amount of pixels that must be maintaned between the character and the edge of the screen 
# We have an offset top viewport margin so that the character is off center
# This makes it look more natural as we see more above ground than below ground
LEFT_VIEWPORT_MARGIN = 840 
RIGHT_VIEWPORT_MARGIN = 840 
BOTTOM_VIEWPORT_MARGIN = 100
TOP_VIEWPORT_MARGIN = 620

WORLD_LENGTH = 10000

class startView(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.set_background_color(arcade.csscolor.BLACK)

        #Menu sound FX
        self.music_list = []
        self.current_song_index = 0
        self.current_player = None
        self.music = None
    
    def play_song(self):
        """ Play the song. """
        self.music = arcade.Sound(self.music_list[self.current_song_index], streaming=True)
        self.current_player = self.music.play(MUSIC_VOLUME)
    
    def setup(self):
        #Setup menu soundtrack
        self.music_list = ["./resources/music/glitch.wav"]
        self.current_song_index = 0


    # Called when this view is to be shown
    def on_show(self):
        
        self.setup()
        # Since we have a sidescrolling mechanic in our game, we need to reset the viewport back to default to display this view
        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1)

    def on_draw(self):
        # Draw this view, we need to do this before we are able to draw anything
        arcade.start_render()
 
        # Draw our background image, we disguise it as a textured rectangle
        self.background = arcade.load_texture("./resources/backgrounds/main_menu.png")
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.background)
        
        """
        # Draw text: we pass the "text", the starting x and starting y of the text, the color, the font size, and where to "anchor" (center, left...)
        arcade.draw_text("Main menu", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.WHITE, font_size=60, anchor_x="center")
        arcade.draw_text("Press space to start", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2-50, arcade.color.WHITE, font_size=45, anchor_x="center")
        """

        

    # Space key pressed event listener to allow use to proceed past the main menu screen
    # When this is called, we will call our gameView class to start the game
    def on_key_press(self, key, modifiers): # Default param2 for this is listener is 'symbol' but we use 'key' to make code more readable
        if key == arcade.key.SPACE:
            self.setup()
            self.current_song_index = 0
            self.play_song() 
            time.sleep(0.75)
            game_view = gameView()
            game_view.setup()
            self.window.show_view(game_view) 


class gameView(arcade.View):
    """
    Our main class for our game application, inherited from the arcade.Window class
    """

    def __init__(self):
        # The super() method allows us to use the __init__() method from the parent superclass, here arcade.Window
        # Set up our game window
        super().__init__()
        self.window.set_mouse_visible(False)

        #We create 'lists' for our sprites, that will later be appended to the SpriteList class
        self.fish_list = None
        self.wall_list = None
        self.player_list = None
        self.background_element_list = None
        self.game_element_list = None
        
        #Need a seperate list for our character sprite
        self.player_sprite = None
        
        #Our physics engine
        self.physics_engine = None

        #Keeping track of our sidescrolling mechanic
        self.view_bottom = 0
        self.view_left = 0

        #Game soundtrack
        self.music_list = []
        self.current_song_index = 0
        self.current_player = None
        self.music = None

        #Game sound FX
        self.sound_list = []
        self.current_sound_index = 0
        self.current_fx_player = None
        self.sound = None

        #10 min Timer, and counter for time elapsed
        self.total_time = 600.0
        self.elapsed_time = 0.0

        #Make clock follow player (these values do not necessarily matter as the position ends up basing off player position)
        self.clock_center_x = -400
        self.clock_center_y = 272
        #We create the same thing as for the clock, for the interaction menu to follow the player
        self.int1_center_x = 1600
        self.int1_center_y = 650

        #Define all the ranges of distances that the character must be in to interact with an object
        #We also create a bool to allow character to interact with objects, only sets to true when in range 
        self.intPrompt = "" #The text to display that corresponds to the object to be interacted with
        
        self.inInteractRange_Sign = False #Sign Bool
        self.sign_low_x = 900 #Sign distance range
        self.sign_high_x = 1300

    def play_song(self):
        """ Play the song. """
        # Stop what is currently playing.
        if self.music:
            self.music.stop()

        # Play the next song
        self.music = arcade.Sound(self.music_list[self.current_song_index], streaming=True)
        self.current_player = self.music.play(MUSIC_VOLUME, 0) #Param: Volume(float), pan(float -1 to 1), Loop?(bool)
        # This is a quick delay. If we don't do this, our elapsed time is 0.0
        # and on_update will think the music is over and advance us to the next
        # song before starting this one.
        time.sleep(0.03)
    
    def play_sound(self):
        self.sound = arcade.Sound(self.sound_list[self.current_sound_index], streaming=True)
        self.current_player = self.sound.play(FX_VOLUME)
    
    def setup(self):
        # This method sets up the game. It is also used to restart the game
        # Creating the spritelists, with the SpriteList class
        self.player_list = arcade.SpriteList()
        self.fish_list = arcade.SpriteList(use_spatial_hash=True) # Passing the use_spatial_hash helps optimize collision detection for objects that spend a lot of time immobile
        self.wall_list = arcade.SpriteList(use_spatial_hash=True) # We don't pass it for our character since he will need to move a lot 
        self.background_element_list = arcade.SpriteList(use_spatial_hash=True)
        self.game_element_list = arcade.SpriteList(use_spatial_hash=True)

        #Setting up our player sprite, and defining its starting coordinates
        img = "./resources/test_sprite.png"
        self.player_sprite = arcade.Sprite(img, 1) # Param 2 defines scaling size 
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = 128
        self.player_list.append(self.player_sprite)


        #For loop to place floors
        #IMPORTANT: The floor level is y=56 
        #To place items on the floor, you do [item].center_y = (imgheight / 2) + 56
        x = -1048
        for i in range(1, (WORLD_LENGTH // 262)):
            wall = arcade.Sprite("./resources/backgrounds/floor2.png", 1)
            wall.center_x = x
            wall.center_y = -75
            self.wall_list.append(wall)
            x += 262 #This is the exact value to respect to the lengths of our floors, as they are 420*262

        # We can use a coordinate list to place our blocks at multiple specific positions:
        block_location_list = [
            [512,96],
            [256,96],
            [768,96]
        ]
        
        for coordinate in block_location_list:
            # Add a block at one of the locations in our list
            wall = arcade.Sprite("./resources/block.png", 0.1)
            wall.position = coordinate
            self.wall_list.append(wall)

        cloud_location_list = [
            [400, 500] # We add a first cloud that always spawns there
        ]
        
        # WE create 2 variables for the x range that our cloud will be placed in
        #This preserves the randonness but makes sure our clouds have somewhat consistent distances between eachother, avoiding disparities/empty patches
        next_cloud_low = -800
        next_cloud_high = -625
        
        for i in range (1, (WORLD_LENGTH // 175)):
            # Loop to randomly add clouds in our background
            # Each iteration will create a list of x, y coordinates for 1 cloud
            to_append = []
            to_append.append(random.randint(next_cloud_low, next_cloud_high))
            to_append.append(random.randint(350, 675)) # Fixed y range to maintain in sky to keep clouds in sky
            cloud_location_list.append(to_append)
            to_append = []
            next_cloud_low += 175
            next_cloud_high += 175


        for coordinate in cloud_location_list:
            # We do the same as the blocks for our clouds
            cloud_1 = arcade.Sprite("./resources/backgrounds/background elements/cloud_1.png", 1.1)
            cloud_2 = arcade.Sprite("./resources/backgrounds/background elements/cloud_2.png", 1.2)
            clouds = [cloud_1, cloud_2]
            cloud = random.choice(clouds) # Random clouds to vary our background
            cloud.position = coordinate
            self.background_element_list.append(cloud)

        #Add all our sprites that correspond to game elements
       
        #Add our sign
        sign = arcade.Sprite("./resources/game elements/sign.png", 0.35)
        sign.center_x = 1100
        sign.center_y = 91
        self.game_element_list.append(sign)
        
        
        #Create our physics engine
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, self.wall_list, GRAVITY)

        #Setup game soundtrack
        self.music_list = ["./resources/music/ambient_1.wav"]

        self.current_song_index = 0

        self.play_song()

        #Setup game sounds
        self.sound_list = ["./resources/music/jump.wav"]

        #Reset our clock to 10 mins and elapsed to 0
        self.total_time = 600.0
        self.elapsed_time = 0.0

    def on_key_press(self, key, modifiers):
        # Called when the user presses a key
        if key == arcade.key.UP or key == arcade.key.W or key == arcade.key.SPACE:
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                self.current_sound_index = 0
                self.play_sound()
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.player_sprite.change_y = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED

        #Default interaction keybind
        elif key == arcade.key.E:
            if self.inInteractRange_Sign:
                #Reset our player movement so that he is not moving when we switch back from the sign view
                self.player_sprite.change_x = 0
                self.player_sprite.change_y = 0
                
                sign_View = signView(self)
                self.window.show_view(sign_View)

        elif key == arcade.key.ESCAPE:
            pause_view = pauseView(self) 
            self.window.show_view(pause_view)

    def on_key_release(self, key, modifers):
        # Called when the user releases a key
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = 0
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = 0
        elif key == arcade.key.ESCAPE: # Make sure that our character does not keep moving if esc is pressed at same time as movement
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

    def on_update(self, delta_time):
        # This is our movement logic. It is called around 60 times a second

        # Moving the player with the physics engine
        self.physics_engine.update()

        self.game_element_list.update()

        # Manage our scrolling mechanic
        
        # Boolean to keep track if we have changed our viewport
        changed = False

        #Scroll left
        left_boundary = self.view_left + LEFT_VIEWPORT_MARGIN
        if self.player_sprite.left < left_boundary:
            self.view_left -= left_boundary - self.player_sprite.left
            changed = True

        #Scroll right
        right_boundary = self.view_left + SCREEN_WIDTH - RIGHT_VIEWPORT_MARGIN
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary
            changed = True

        #Scroll up
        top_boundary = self.view_bottom + SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary
            changed = True

        #Scroll down
        bottom_boundary = self.view_bottom + BOTTOM_VIEWPORT_MARGIN
        if self.player_sprite.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player_sprite.bottom
            changed = True

        if changed:
            # We specify to scroll to integers, or else we can end up with pixels not correctly on the screen
            self.view_bottom = int(self.view_bottom)
            self.view_left = int(self.view_left)

            # We call this method to set the viewport (what coordinates we can see)
            # We pass 4 positional arguments, all of type float - arcade.set_viewport(left, right, bottom, top)
            arcade.set_viewport(self.view_left, SCREEN_WIDTH + self.view_left, self.view_bottom, SCREEN_HEIGHT + self.view_bottom)

            #Make our timer follow our player
            #This simply waits for any change in player x/y and then adjusts the location of a timer, keeping a constant distance value
            self.clock_center_x = (self.player_sprite.center_x - 800)
            self.clock_center_y = (self.player_sprite.center_y + 500)     

            self.int1_center_x = (self.player_sprite.center_x + 445)
            self.int1_center_y = (self.player_sprite.center_y + 500)     

        #Increment down our total time and up our elapsed time
        self.total_time -= delta_time
        self.elapsed_time += delta_time

        #Detect if the player is near an element he can interact with
        #here we detect if the player can interact with the sign, and make sure to only allow this if the player is on the ground
        if self.player_sprite.center_x in range (self.sign_low_x, self.sign_high_x) and self.physics_engine.can_jump():
            self.intPrompt = "Press E to interact with Sign"
            self.inInteractRange_Sign = True
        else:
            self.intPrompt = ""
            self.inInteractRange_Sign = False

    def on_draw(self):
        # Method to render our screen
        arcade.start_render()
        arcade.set_background_color(arcade.csscolor.DODGER_BLUE)  # CSS color documentation: https://arcade.academy/arcade.csscolor.html

        self.wall_list.draw()
        self.fish_list.draw()
        self.background_element_list.draw()
        self.game_element_list.draw()
        self.player_list.draw() # We draw our player last so that he is in front of all other elements

        clock_minutes = int(self.total_time) // 60
        clock_seconds = int(self.total_time) % 60

        # Adding the '02d' in our string formats our int to have a width of 2
        # This adds automatic padding with 0's if time is in single digit
        clock = f'Time: {clock_minutes:02d}:{clock_seconds:02d}' 
        arcade.draw_text(clock, self.clock_center_x, self.clock_center_y, arcade.color.BLACK, 30)
       
        #This will draw our interactions that are currently available
        #on_update() will automatically set intPrompt="" when no interaction available, and so no text will be drawn
        arcade.draw_text(self.intPrompt, self.int1_center_x, self.int1_center_y, arcade.csscolor.BROWN, 30)
        
        elapsed_minutes = int(self.elapsed_time) // 60
        elapsed_seconds = int(self.elapsed_time) % 60

        """
        Can choose to add the display of elapsed time at some point - not needed right now
        elapsed = f'Elapsed: {elapsed_minutes:02d} : {elapsed_seconds:02d}'
        arcade.draw_text(elapsed, -400, 300, arcade.color.BLACK, 30)
        """
        #Make the game exit when we have hit over 10 minutes
        if self.elapsed_time > 600.0:
            #We will later add a different game over view that is swapped to when the time is elapsed
            time.sleep(0.5)
            sys.exit(0)


class pauseView(arcade.View):
    
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view

    def on_show(self):
        arcade.set_background_color(arcade.csscolor.LIGHT_SLATE_GRAY)
        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1)
    
    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Pause menu", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.WHITE, font_size=60, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE or key == arcade.key.ENTER:
            self.window.show_view(self.game_view)

#All the different arcade.view classes for our game elements
class signView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view

    def on_show(self):
        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1) #center our view just to make sure
    
    def on_draw(self):
        arcade.start_render()
        
        self.background = arcade.load_texture("./resources/game elements/signView.png")
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.background)
        
        arcade.draw_text("Press E to exit", 1400, 650, arcade.csscolor.BROWN, 30)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.E:
            self.window.show_view(self.game_view)

def main():
    # Our main method to run our game
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE) # We need to create an instance of our game arcade.Window
    start_view = startView() 
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()

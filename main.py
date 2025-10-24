import json
import os
import math
import myimgui as mig
from slimgui import imgui as ig
import glfw

# "aequalitas": [ "cognitio", "ordo" ],
# "vesania": [ "cognitio", "vitium" ],
# "primordium": [ "vacuos", "motus" ],
# "astrum": [ "lux", "primordium" ],
# "gloria": [ "humanus", "iter" ],
# "terminus": [ "lucrum", "alienis" ],
# "caelum": [ "vitium", "metallum" ],
# "tabernus": [ "tutamen", "iter" ]

aspects : dict = None
with open('aspects.json') as aspects_file:
    aspects = json.loads(aspects_file.read())
    assert aspects != None

class TRSApp(mig.ImguiApp):
    def setup(self):
        self.hex_texture = mig.load_texture("hex.png")
        self.complexity = 3
        self.rows = 1
        self.cols = 1
        self.button_size = (40, 40)

    def down_left(self, pos, count):
        next_pos = self.set_and_get_screen_pos(pos, (-34, 22))
        ig.image_button(f'grid_img_button{count}', self.hex_texture, image_size=self.button_size)
        return next_pos
    def down_right(self, pos, count):
        next_pos = self.set_and_get_screen_pos(pos, (34, 22))
        ig.image_button(f'grid_img_button{count}', self.hex_texture, image_size=self.button_size)
        return next_pos
    def right(self, pos, count):
        next_pos = self.set_and_get_screen_pos(pos, (68, 0))
        ig.image_button(f'grid_img_button{count}', self.hex_texture, image_size=self.button_size)
        return next_pos
    def left(self, pos, count):
        next_pos = self.set_and_get_screen_pos(pos, (-68, 0))
        ig.image_button(f'grid_img_button{count}', self.hex_texture, image_size=self.button_size)
        return next_pos

    def build_grid(self):
        ig.begin_child("ch1", child_flags = ig.ChildFlags.AUTO_RESIZE_X | ig.ChildFlags.AUTO_RESIZE_Y | ig.ChildFlags.BORDERS)
        ig.push_style_color(ig.Col.BUTTON, (0,0,0,0))

        left_padding = ((self.complexity - 1) * 34)
        ig.dummy((left_padding, 0))
        ig.same_line()
        ig.set_next_item_allow_overlap()
        pos = ig.get_cursor_screen_pos()
        ig.image_button(f'grid_img_button{0}', self.hex_texture, image_size=self.button_size)
        count = 1

        # Top rows (increasing length)
        right = True
        for row_length in range(2, self.complexity+1):
            pos = self.down_left(pos, count) if right else self.down_right(pos, count)
            count += 1
            for x in range(1, row_length):
                pos = self.right(pos, count) if right else self.left(pos, count)
                count += 1
            right = not right

        # Middle row (maximum length)
        for c in range(0, self.complexity-1):
            pos = self.down_right(pos, count) if right else self.down_left(pos, count)
            count += 1
            for x in range(1, self.complexity-1):
                pos = self.right(pos, count) if right else self.left(pos, count)
                count += 1
            right = not right
            pos = self.down_left(pos, count) if right else self.down_right(pos, count)
            count += 1
            for x in range(1, self.complexity):
                pos = self.right(pos, count) if right else self.left(pos, count)
                count += 1
            right = not right

        # Bottom rows (decreasing length)
        for row_length in range(self.complexity-1, 0, -1):
            pos = self.down_right(pos, count) if right else self.down_left(pos, count)
            count += 1
            for x in range(1, row_length):
                pos = self.right(pos, count) if right else self.left(pos, count)
                count += 1
            right = not right

        ig.pop_style_color()
        ig.end_child()

    def set_and_get_screen_pos(self, pos, offset = (0.0, 0.0)):
        ig.set_next_item_allow_overlap()
        ig.set_cursor_screen_pos((pos[0] + offset[0], pos[1] + offset[1]))
        pos = ig.get_cursor_screen_pos()
        return pos

    def mainloop(self):
        ig.set_next_window_pos((0, 0), ig.Cond.ONCE)
        ig.set_next_window_size(glfw.get_window_size(self._glfw_window), ig.Cond.ALWAYS)
        ig.begin("a", flags = ig.WindowFlags.NO_MOVE | ig.WindowFlags.NO_RESIZE | ig.WindowFlags.NO_TITLE_BAR)
        
        if (ig.button("+##A")):
            self.complexity += 1
        ig.same_line()
        if (ig.button("-##A")):
            self.complexity -= 1
        ig.same_line()
        ig.text(f"{self.complexity} complexity")
        self.build_grid()
        ig.end()

app = TRSApp(title = 'Thaumcraft Research Solver')
app.run()
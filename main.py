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
        self.complexity = 2
        self.rows = 1
        self.cols = 1

    def mainloop(self):
        ig.set_next_window_pos((0, 0), ig.Cond.ONCE)
        ig.set_next_window_size(glfw.get_window_size(self._glfw_window), ig.Cond.ALWAYS)
        ig.begin("a", flags = ig.WindowFlags.NO_MOVE | ig.WindowFlags.NO_RESIZE | ig.WindowFlags.NO_TITLE_BAR)
        
        if (ig.button("+##A")):
            self.rows += 1
        ig.same_line()
        if (ig.button("-##A")):
            self.rows -= 1
        ig.same_line()
        ig.text(f"{self.rows} rows")
        ig.new_line()

        if (ig.button("+##B")):
            self.cols += 1
        ig.same_line()
        if (ig.button("-##B")):
            self.cols -= 1
        ig.same_line()
        ig.text(f"{self.cols} cols")
        ig.new_line()

        button_size = (40, 40)
        offset = 14

        ig.push_style_color(ig.Col.BUTTON, (0,0,0,0))
        
        for row in range(self.rows):
            # Offset every other row
            ig.push_style_var(ig.StyleVar.ITEM_SPACING, (20, -23))
            if row % 2 == 1:
                ig.dummy((offset, 0))
                ig.same_line()
            for col in range(self.cols):
                if col > 0:
                    ig.same_line()
                ig.set_next_item_allow_overlap()
                if ig.image_button(f'{row},{col}', self.hex_texture, image_size=button_size):
                    pass
            ig.new_line()
            ig.pop_style_var()
        ig.pop_style_color()
        
        ig.end()

app = TRSApp(title = 'Thaumcraft Research Solver')
app.run()
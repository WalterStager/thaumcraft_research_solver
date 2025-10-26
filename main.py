import json
import math
import numpy as np
import myimgui as mig
from slimgui import imgui as ig
import glfw
from algo import AspectRelations, HexGrid

"""
u     0,  44    -1,  0
ur   34,  22     0, -1
dr   34, -22     1, -1
d     0, -44     1,  0
dl  -34, -22     0,  1
ul  -34,  22    -1,  1


1, 0 = 0, -44
0, 1 = -34, -22

pos = (r*-34, q*-34 + r*-22)
"""

class TRSApp(mig.ImguiApp):
    def setup(self):
        self.global_scale_factor = 1
        self.calculate_scaling()

        self.grid_size = 3
        self.grid = HexGrid(self.grid_size)
        self.full_grid = HexGrid(self.grid_size)
        self.aspect_rels = AspectRelations()
        self.placed_aspects : dict[int, str] = {}
        
        self.hex_texture = mig.load_texture("hex.png")

        with open('aspects.json') as aspects_file:
            self.aspects : dict[str, None | list[str]] = json.loads(aspects_file.read())
            assert self.aspects != None
        self.aspect_textures = {}
        for aspect in self.aspects.keys():
            self.aspect_textures[aspect] = mig.load_texture(f"templates/{aspect}.png")

    def drop_target(self, id, grid_id, pos):
        aspect = self.placed_aspects.get(grid_id)
        if (aspect in self.aspect_textures):
            ig.set_cursor_pos(pos)
            if (ig.image_button(f"grid_image_button_{id}", self.aspect_textures[aspect], image_size=self.button_size)):
                self.placed_aspects.pop(grid_id)
            if (ig.begin_drag_drop_target()):
                payload : ig.Payload = ig.accept_drag_drop_payload("aspect_dd", ig.DragDropFlags.NONE)
                if (payload != None):
                    self.placed_aspects[grid_id] = payload.data().decode('utf-8')
                ig.end_drag_drop_target()
            
            # disabled background
            ig.set_cursor_pos(pos)
            ig.begin_disabled()
            ig.image_button(f"grid_image_button_bg_{id}", self.hex_texture, image_size=self.button_size, tint_col=(0.4, 0.6, 0.4, 0.5))
            ig.end_disabled()
        elif (not grid_id in self.grid.disabled_nodes):
            ig.set_cursor_pos(pos)
            if (ig.image_button(f"grid_image_button_{id}", self.hex_texture, image_size=self.button_size)):
                # self.grid.remove_id(grid_id)
                self.grid.disable_id(grid_id)
            if (ig.begin_drag_drop_target()):
                payload : ig.Payload = ig.accept_drag_drop_payload("aspect_dd", ig.DragDropFlags.NONE)
                if (payload != None):
                    self.placed_aspects[grid_id] = payload.data().decode('utf-8')
                ig.end_drag_drop_target()
        else:
            ig.set_cursor_pos(pos)
            if (ig.image_button(f"grid_image_button_dis_{id}", self.hex_texture, image_size=self.button_size, tint_col=(0.6, 0.4, 0.4, 0.5))):
                # self.grid.add_node(self.full_grid., grid_id)
                self.grid.enable_id(grid_id)


    def build_grid(self):
        ig.begin_child("ch1", child_flags = ig.ChildFlags.AUTO_RESIZE_X | ig.ChildFlags.AUTO_RESIZE_Y | ig.ChildFlags.BORDERS)
        ig.push_style_color(ig.Col.BUTTON, (0,0,0,0))
        button_coords : list[tuple[int, int]] = []
        count = 0
        for node_id in self.full_grid.all_nodes():
            coords = self.full_grid.id_to_coord.get(node_id)
            pos = (coords[1] * self.horz_spacing, (coords[0] * self.vert_spacing1) + (coords[1] * self.vert_spacing2), node_id)
            button_coords.append(pos)
        if (len(button_coords) != 0):
            xs, ys, _ = zip(*button_coords)
            min_x = min(xs)
            min_y = min(ys)
            x_offset = abs(min(0, min_x))
            y_offset = abs(min(0, min_y))
            for x, y, id in button_coords:
                self.drop_target(count, id, (x + x_offset, y + y_offset))
                count += 1
        ig.pop_style_color()
        ig.end_child()
    
    def build_aspects(self):
        ig.begin_child("ch2", child_flags = ig.ChildFlags.AUTO_RESIZE_X | ig.ChildFlags.AUTO_RESIZE_Y | ig.ChildFlags.BORDERS)
        cols = 6
        count = 0
        for aspect in self.aspects.keys():
            
            ig.image_button(f"aspect_img_button_{aspect}", self.aspect_textures[aspect], image_size=self.button_size)
            ig.set_item_tooltip(f"[{', '.join(self.aspect_rels.aspect_children.get(aspect, []))}] > {aspect} > [{', '.join(self.aspect_rels.aspect_parents.get(aspect, []))}]")
            if (ig.begin_drag_drop_source()):
                ig.set_drag_drop_payload("aspect_dd", aspect.encode('utf-8'))
                ig.end_drag_drop_source()
            count += 1
            if (count % cols != 0):
                ig.same_line()
        ig.end_child()

    def reset(self):
        self.placed_aspects = {}
        self.grid = HexGrid(self.grid_size)
        self.full_grid = HexGrid(self.grid_size)

    def solve(self, first = True):
        starting_nodes = list(self.placed_aspects.keys())
        if (len(self.placed_aspects.keys()) < 2):
            return
        
        for start_node in starting_nodes:
            others : set[int] = set(self.placed_aspects.keys())
            others.remove(start_node)
            print(start_node, others)

            path_length = 0
            while (path_length < self.grid_size * 2):
                grid_path = self.grid.find_path_minimum_length(start_node, others, path_length)
                if (grid_path == None):
                    continue
                aspect_path = self.aspect_rels.find_path_exact_length(self.placed_aspects[grid_path[0]], self.placed_aspects[grid_path[-1]], len(grid_path))
                if (aspect_path == None):
                    path_length = len(grid_path) + 1
                    continue
                
                self.placed_aspects.update(zip(grid_path, aspect_path))
                break
        if (first):
            self.solve(False)

    def calculate_scaling(self):
        self.global_scale_factor = max(0.1, self.global_scale_factor)
        self.global_scale_factor = min(5, self.global_scale_factor)
        self._font_scale = 25 * self.global_scale_factor
        button_scale_size = int(80 * self.global_scale_factor)
        margin = button_scale_size // 13
        self.button_size = (button_scale_size, button_scale_size)
        self.horz_spacing = -1 * (((3 * button_scale_size) // 4) + margin)
        self.vert_spacing1 = -1 * (button_scale_size + margin)
        self.vert_spacing2 = -1 * ((button_scale_size + margin) // 2)

    def mainloop(self):
        ig.set_next_window_pos((0, 0), ig.Cond.ONCE)
        ig.set_next_window_size(glfw.get_window_size(self._glfw_window), ig.Cond.ALWAYS)
        ig.begin("Main window", flags = ig.WindowFlags.NO_MOVE | ig.WindowFlags.NO_RESIZE | ig.WindowFlags.NO_COLLAPSE | ig.WindowFlags.MENU_BAR | ig.WindowFlags.NO_TITLE_BAR | ig.WindowFlags.ALWAYS_AUTO_RESIZE)

        if (ig.begin_menu_bar()):
            if (ig.begin_menu("Options")):
                ig.set_next_item_width(ig.calc_text_size("UI Scale")[0] + 80 * self.global_scale_factor)
                res, temp_gsf = ig.input_float("UI Scale", self.global_scale_factor, 0.1, 1, flags = ig.InputTextFlags.NONE)
                if (res):
                    self.global_scale_factor = temp_gsf
                    self.calculate_scaling()

                ig.end_menu()
            ig.end_menu_bar()

        if (ig.button("reset")):
            self.reset()
        ig.same_line()
        if (ig.button("solve")):
            self.solve()
        ig.same_line()
        ig.set_next_item_width(ig.calc_text_size("grid size")[0] + 80 * self.global_scale_factor)
        res, temp_size = ig.input_int("grid size", self.grid_size, 1, 1)
        if (res):
            self.grid_size = temp_size
            self.grid_size = max(2, self.grid_size)
            self.grid_size = min(10, self.grid_size)
            self.reset()

        self.build_aspects()
        ig.same_line()
        self.build_grid()
        ig.end()

app = TRSApp(title = 'Thaumcraft Research Solver', width = 1500, height = 1100)
app.run()
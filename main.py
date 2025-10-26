import json
import math
import numpy as np
import myimgui as mig
from slimgui import imgui as ig
import glfw
from pathlib import Path
import atexit
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
        self.settings_path = Path(__file__).with_name("config.json")
        self.load_settings()
        atexit.register(self.save_settings)
        self.calculate_scaling()

        self.grid_size = 3
        self.grid = HexGrid(self.grid_size)
        self.full_grid = HexGrid(self.grid_size)
        self.aspect_rels = AspectRelations()
        self.placed_aspects : dict[int, str] = {}
        
        self.hex_texture = mig.load_texture("hex.png")
        self.invisible_table_flags = ig.TableFlags.NO_BORDERS_IN_BODY | ig.TableFlags.NO_SAVED_SETTINGS
        self.invisible_column_flags = ig.TableColumnFlags.NO_REORDER | ig.TableColumnFlags.NO_RESIZE | ig.TableColumnFlags.NO_SORT | ig.TableColumnFlags.NO_HEADER_LABEL

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
    
    def build_aspect_tooltip(self, aspect : str):
        if (ig.begin_tooltip()):
            num_cols = len(self.aspect_rels.aspect_relations[aspect]) + 3
            aspect_names1 = list(self.aspect_rels.aspect_children.get(aspect, []))
            aspect_names2 = list(self.aspect_rels.aspect_parents.get(aspect, []))
            aspect_textures1 = [self.aspect_textures[a] for a in aspect_names1]
            aspect_textures2 = [self.aspect_textures[a] for a in aspect_names2]
            if (ig.begin_table(f"aspect_img_button_{aspect}_tooltip", num_cols, ig.TableFlags.NO_SAVED_SETTINGS | ig.TableFlags.BORDERS_INNER_V)):
                for i in range(num_cols):
                    ig.table_setup_column(f"aspect_img_button_{aspect}_tooltip_col{i}", self.invisible_column_flags)
                # text labels
                ig.table_next_row()
                index = 0
                for aspect_name in aspect_names1:
                    ig.table_set_column_index(index)
                    index += 1
                    ig.text(aspect_name)

                # skip a column before and after hovered aspect
                index += 1
                ig.table_set_column_index(index)
                ig.text(aspect)
                index += 2

                for aspect_name in aspect_names2:
                    ig.table_set_column_index(index)
                    index += 1
                    ig.text(aspect_name)

                # images
                ig.table_next_row()
                index = 0
                for aspect_texture in aspect_textures1:
                    ig.table_set_column_index(index)
                    index += 1
                    ig.image(aspect_texture, self.button_size)

                # show separators bofre and after hovered aspect
                ig.table_set_column_index(index)
                index += 1
                ig.text(">")
                ig.table_set_column_index(index)
                index += 1
                ig.image(self.aspect_textures[aspect], self.button_size)
                ig.table_set_column_index(index)
                index += 1
                ig.text(">")

                for aspect_texture in aspect_textures2:
                    ig.table_set_column_index(index)
                    index += 1
                    ig.image(aspect_texture, self.button_size)
                
                ig.end_table()
            ig.end_tooltip()

    def build_aspects(self):
        ig.begin_child("ch2", child_flags = ig.ChildFlags.AUTO_RESIZE_X | ig.ChildFlags.AUTO_RESIZE_Y | ig.ChildFlags.BORDERS)
        cols = 6
        count = 0
        for aspect in self.aspects.keys():
            ig.image_button(f"aspect_img_button_{aspect}", self.aspect_textures[aspect], image_size=self.button_size)
            if (ig.is_item_hovered()):
                self.build_aspect_tooltip(aspect)
            # ig.set_item_tooltip(f"[{', '.join(self.aspect_rels.aspect_children.get(aspect, []))}] > {aspect} > [{', '.join(self.aspect_rels.aspect_parents.get(aspect, []))}]")
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

    def solve(self):
        contiguous_sets = self.grid.split_contiguous_nodes(self.placed_aspects.keys())
        iters = 0
        while (len(contiguous_sets) > 1 and iters < 100):
            print(contiguous_sets, iters)
            setA = contiguous_sets[0]
            added_nodes = False
            # todo: save all the solutions and pick the best one?
            for node in setA:
                others = [x for sl in contiguous_sets[1:] for x in sl]
                path_length = 0
                while (path_length < self.grid_size * 2):
                    grid_path = self.grid.find_path_minimum_length(node, others, path_length)
                    if (grid_path == None):
                        continue
                    aspect_path = self.aspect_rels.find_path_exact_length(self.placed_aspects[grid_path[0]], self.placed_aspects[grid_path[-1]], len(grid_path)-1)
                    if (aspect_path == None):
                        path_length = len(grid_path) + 1
                        continue
                    added_nodes = True
                    self.placed_aspects.update(zip(grid_path[1:-1], aspect_path[1:-1]))
                    break
                if (added_nodes):
                    break
            contiguous_sets = self.grid.split_contiguous_nodes(self.placed_aspects.keys())
            iters += 1

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

    def load_settings(self):
        if not hasattr(self, "settings_path") or not self.settings_path.exists():
            return
        try:
            with self.settings_path.open("r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            return
        scale = data.get("ui_scale")
        if isinstance(scale, (int, float)):
            self.global_scale_factor = max(0.1, min(5, float(scale)))
        window = self._glfw_window
        size = data.get("window_size")
        if size:
            print(f"[config] load window_size={size}")
        if window and isinstance(size, (list, tuple)) and len(size) == 2:
            try:
                width = max(200, int(size[0]))
                height = max(200, int(size[1]))
                glfw.set_window_size(window, width, height)
            except (TypeError, ValueError):
                pass
        pos = data.get("window_position")
        if window and isinstance(pos, (list, tuple)) and len(pos) == 2:
            try:
                glfw.set_window_pos(window, int(pos[0]), int(pos[1]))
            except (TypeError, ValueError):
                pass

    def save_settings(self):
        if not hasattr(self, "settings_path"):
            return
        window = self._glfw_window
        window_size = window_pos = None
        if window:
            try:
                window_size = glfw.get_window_size(window)
                window_pos = glfw.get_window_pos(window)
            except glfw.GLFWError:
                window_size = window_pos = None
        data = {"ui_scale": self.global_scale_factor}
        if window_size:
            print(f"[config] save window_size={window_size}")
            data["window_size"] = list(window_size)
        if window_pos:
            data["window_position"] = list(window_pos)
        try:
            with self.settings_path.open("w", encoding="utf-8") as config_file:
                json.dump(data, config_file, indent=2)
        except OSError:
            pass

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

        if (ig.begin_table("Main window table", 2, self.invisible_table_flags)):
            ig.table_setup_column("Main window col 1", self.invisible_column_flags)
            ig.table_setup_column("Main window col 2", self.invisible_column_flags)
            
            ig.table_next_row()
            ig.table_set_column_index(0)
            if (ig.button("reset")):
                self.reset()
            ig.same_line()
            if (ig.button("solve")):
                self.solve()
            ig.table_set_column_index(1)
            ig.set_next_item_width(ig.calc_text_size("grid size")[0] + 80 * self.global_scale_factor)
            res, temp_size = ig.input_int("grid size", self.grid_size, 1, 1)
            if (res):
                self.grid_size = temp_size
                self.grid_size = max(2, self.grid_size)
                self.grid_size = min(10, self.grid_size)
                self.reset()

            ig.table_next_row()
            ig.table_set_column_index(0)
            self.build_aspects()
            ig.table_set_column_index(1)
            self.build_grid()
            ig.end_table()
        ig.end()

app = TRSApp(title = 'Thaumcraft Research Solver', width = 1500, height = 1100)
app.run()
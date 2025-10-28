import os
import glfw
import OpenGL.GL as gl
from slimgui import imgui
from slimgui.integrations.glfw import GlfwRenderer
from PIL import Image

def load_texture(filename):
    assert filename != None
    # assert os.path.isfile(filename)
    with Image.open(filename) as img:
        img = img.convert("RGBA")
        width, height = img.size
        pixels = img.tobytes()

        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexParameter(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameter(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ROW_LENGTH, 0)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, pixels)
        return texture_id

# def _download_cached(url, cache_dir="thaumcraft_research_solver") -> str:
#     os.makedirs(os.path.expanduser(f"~/.cache/{cache_dir}"), exist_ok=True)
#     filename = os.path.basename(url)
#     cache_path = os.path.expanduser(f"~/.cache/{cache_dir}/{filename}")
#     if not os.path.exists(cache_path):
#         r = requests.get(url)
#         r.raise_for_status()
#         with open(cache_path, 'wb') as f:
#             f.write(r.content)
#     return cache_path

def load_font():
    # _download_cached('https://github.com/jnmaloney/WebGui/raw/master/data/xkcd-script.ttf')
    with open("sans.ttf", 'rb') as f:
        font_data = f.read()
        return imgui.get_io().fonts.add_font_from_memory_ttf(font_data, 24)

_esc_pressed = False
def _key_callback(_window, key, _scan, action, _mods):
    global _esc_pressed
    if action == glfw.PRESS and key == glfw.KEY_ESCAPE:
        _esc_pressed = True

class ImguiApp:
    def __init__(self, title = "myimgui window", width = 1280, height = 720):
        self._renderer : GlfwRenderer = None
        self._glfw_window = None
        self._font = None
        self._title = title
        self._width = width
        self._height = height
        self._font_scale = 0

    def __dispose__(self):
        self._imgui_teardown()

    def run(self):
        self._mainloop_wrapper()

    def _imgui_setup(self):
        # GLFW init.
        glfw.init()

        # OpenGL context version, required for operation on macOS.
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.VISIBLE, True)

        self._glfw_window = glfw.create_window(width=self._width, height=self._height, title=self._title, monitor=None, share=None)
        glfw.make_context_current(self._glfw_window)

        # Imgui init.
        imgui.create_context()
        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags.NAV_ENABLE_KEYBOARD
        self._renderer = GlfwRenderer(self._glfw_window, prev_key_callback=_key_callback)

        self._font = load_font()

    def _imgui_teardown(self):
        self._renderer.shutdown()
        imgui.destroy_context(None)

    def _mainloop_wrapper(self):
        self._imgui_setup()
        self.setup()
        while not (glfw.window_should_close(self._glfw_window) or _esc_pressed):
            glfw.poll_events()

            # Start new imgui frame.
            gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))
            self._renderer.new_frame()
            imgui.new_frame()
            imgui.push_font(self._font, self._font_scale)

            self.mainloop()

            # ImGui frame rendering.
            imgui.pop_font()
            imgui.render()
            self._renderer.render(imgui.get_draw_data())

            # Swap buffers.
            glfw.swap_buffers(self._glfw_window)
        self.teardown()
        self._imgui_teardown()

    def setup(self):
        self.count = 0

    def teardown(self):
        pass

    def mainloop(self):
        imgui.set_next_window_size((400, 400), imgui.Cond.FIRST_USE_EVER)
        imgui.begin('Application Window')
        if imgui.button("Click me!"):
            self.count += 1
        imgui.same_line()
        imgui.text(f"Clicked {self.count} times")
        imgui.end()



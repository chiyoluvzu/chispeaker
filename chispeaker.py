#!/usr/bin/env python3
import gi, subprocess, threading, shutil

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

SINK = "VirtualMic"
LOOP_SINK = "VirtualMicLoopback"

PKG_MAP = {
    "apt": {
        "pactl": "pulseaudio-utils",
        "grep": "grep",
        "awk": "gawk",
        "gespeaker": "gespeaker",
        "pgrep": "procps",
        "sleep": "coreutils"
    },
    "pacman": {
        "pactl": "pulseaudio",
        "grep": "grep",
        "awk": "gawk",
        "gespeaker": "gespeaker",
        "pgrep": "procps-ng",
        "sleep": "coreutils"
    }
}

def detect_distro():
    if shutil.which("apt"):
        return "apt"
    elif shutil.which("pacman"):
        return "pacman"
    return None

def animate_text(buffer, text, delay=30):
    def type_char(index=0):
        if index < len(text):
            end_iter = buffer.get_end_iter()
            buffer.insert(end_iter, text[index])
            GLib.timeout_add(delay, type_char, index + 1)
        return False
    type_char()

class ChispeakerApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="chispeaker")
        self.set_border_width(10)
        self.set_default_size(500, 320)

        css = """
        * {
            background-color: #000000;
            color: #ff00d9;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        GtkButton {
            background-color: #1a001a;
            border-radius: 6px;
            padding: 10px;
            border: 1px solid #ff00d9;
        }
        GtkButton:hover {
            background-color: #ff00d9;
            color: #000000;
        }
        GtkTextView {
            background-color: #0a001a;
            border: 1px solid #ff00d9;
            padding: 8px;
        }
        GtkScrolledWindow {
            border-radius: 6px;
            border: 1px solid #ff00d9;
        }
        GtkWindow {
            background-color: #000000;
        }
        """

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        title_label = Gtk.Label(label="chispeaker")
        title_label.set_name("title")
        main_box.pack_start(title_label, False, False, 0)

        desc_label = Gtk.Label(label="ez tts app frm raptorbytes")
        main_box.pack_start(desc_label, False, False, 0)

        self.log_buf = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buf)
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.log_view)
        main_box.pack_start(scrolled, True, True, 0)

        btn_row = Gtk.Box(spacing=10)
        main_box.pack_start(btn_row, False, False, 0)

        self.btn_start = Gtk.Button(label="run it")
        self.btn_start.connect("clicked", self.on_start)
        btn_row.pack_start(self.btn_start, True, True, 0)

        self.btn_quit = Gtk.Button(label="kill it")
        self.btn_quit.connect("clicked", Gtk.main_quit)
        btn_row.pack_start(self.btn_quit, True, True, 0)

        self.title_label = title_label
        self.desc_label = desc_label
        self.btn_row = btn_row
        self.scrolled = scrolled

        title_label.set_opacity(0)
        desc_label.set_opacity(0)
        scrolled.set_opacity(0)
        btn_row.set_opacity(0)

        GLib.timeout_add(300, self.fade_in_widget, self.title_label, 0.0)
        GLib.timeout_add(700, self.fade_in_widget, self.desc_label, 0.0)
        GLib.timeout_add(1100, self.fade_in_widget, self.scrolled, 0.0)
        GLib.timeout_add(1500, self.fade_in_widget, self.btn_row, 0.0)
        GLib.timeout_add(2000, lambda: self.log("booted into chispeaker.\n"), 0)

        self.running = False
        self.distro = detect_distro()
        if not self.distro:
            self.log("no pkg mgr found. not today.")
            self.btn_start.set_sensitive(False)
        else:
            self.log(f"pkg mgr: {self.distro} detected")

    def fade_in_widget(self, widget, opacity):
        if opacity >= 1.0:
            widget.set_opacity(1.0)
            return False
        widget.set_opacity(opacity)
        GLib.timeout_add(30, self.fade_in_widget, widget, opacity + 0.1)
        return False

    def log(self, msg, animated=True):
        if animated:
            GLib.idle_add(self._log_animated, msg)
        else:
            GLib.idle_add(self._log, msg)

    def _log(self, msg):
        end = self.log_buf.get_end_iter()
        self.log_buf.insert(end, msg + "\n")
        self.log_view.scroll_to_iter(self.log_buf.get_end_iter(), 0.0, True, 0, 0)

    def _log_animated(self, msg):
        animate_text(self.log_buf, msg + "\n")
        return False

    def run_cmd(self, cmd, chk=True):
        self.log(f"$ {' '.join(cmd)}")
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            self.log(out.strip())
            return out.strip()
        except subprocess.CalledProcessError as e:
            self.log(f"\u00af\\_(\u30c4)_/\u00af error:\n{e.output.strip()}")
            if chk:
                raise
            return None

    def prompt_install(self, missing_pkgs):
        pkg_list = ", ".join(missing_pkgs)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"missing: {pkg_list}\ninstall now?"
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def install_pkgs(self, pkgs):
        if self.distro == "apt":
            self.run_cmd(["sudo", "apt", "update"], chk=False)
            cmd = ["sudo", "apt", "install", "-y"] + pkgs
        elif self.distro == "pacman":
            self.run_cmd(["sudo", "pacman", "-Sy"], chk=False)
            cmd = ["sudo", "pacman", "-S", "--noconfirm"] + pkgs
        else:
            self.log("cannot install on this rig")
            return False
        self.log(f"installing {', '.join(pkgs)}")
        try:
            self.run_cmd(cmd)
            return True
        except Exception as e:
            self.log(f"nah, failed: {e}")
            return False

    def on_start(self, btn):
        if self.running:
            self.log("already going")
            return
        self.running = True
        self.btn_start.set_sensitive(False)
        self.log("booting...\n")
        threading.Thread(target=self.setup, daemon=True).start()

    def setup(self):
        try:
            missing_cmds = []
            missing_pkgs = []
            pkg_map = PKG_MAP.get(self.distro, {})
            for c in ["pactl", "grep", "awk", "gespeaker", "pgrep", "sleep"]:
                if not shutil.which(c):
                    missing_cmds.append(c)
                    missing_pkgs.append(pkg_map.get(c, c))

            if missing_pkgs:
                self.log(f"missing cmds: {', '.join(missing_cmds)}")
                if self.prompt_install(missing_pkgs):
                    success = self.install_pkgs(missing_pkgs)
                    if not success:
                        self.log("install failed. bailing.")
                        self.running = False
                        GLib.idle_add(self.btn_start.set_sensitive, True)
                        return
                    else:
                        self.log("done. restart me.")
                        self.running = False
                        GLib.idle_add(self.btn_start.set_sensitive, True)
                        return
                else:
                    self.log("install no. abort.")
                    self.running = False
                    GLib.idle_add(self.btn_start.set_sensitive, True)
                    return

            self.run_cmd(["pactl", "load-module", "module-null-sink", f"sink_name={SINK}", f"sink_properties=device.description={SINK}"])
            GLib.idle_add(GLib.timeout_add_seconds, 1, lambda: None)

            srcs = self.run_cmd(["pactl", "list", "short", "sources"])
            mon_src = None
            for l in srcs.splitlines():
                if f"{SINK}.monitor" in l:
                    mon_src = l.split()[1]
                    break

            if not mon_src:
                self.log(f"no monitor for {SINK}")
                self.running = False
                GLib.idle_add(self.btn_start.set_sensitive, True)
                return

            self.run_cmd(["pactl", "load-module", "module-null-sink", f"sink_name={LOOP_SINK}", f"sink_properties=device.description={LOOP_SINK}"])
            self.run_cmd(["pactl", "load-module", "module-loopback", f"source={mon_src}", f"sink={LOOP_SINK}", "latency_msec=1"])

            try:
                subprocess.check_output(["pgrep", "-x", "gespeaker"])
                self.log("gespeaker up")
            except subprocess.CalledProcessError:
                subprocess.Popen(["gespeaker"])
                self.log("started gespeaker")

            app_sink = None
            for _ in range(10):
                sink_inps = self.run_cmd(["pactl", "list", "sink-inputs", "short"], chk=False) or ""
                for l in sink_inps.splitlines():
                    if "gespeaker" in l.lower():
                        app_sink = l.split()[0]
                        break
                if app_sink:
                    break
                GLib.idle_add(GLib.timeout_add_seconds, 1, lambda: None)

            if not app_sink:
                self.log("cant find gespeaker input, try pavucontrol")
            else:
                self.log(f"move gespeaker input to {SINK}")
                self.run_cmd(["pactl", "move-sink-input", app_sink, SINK], chk=False)

            self.log("\nall set.")
            self.log(f"set input to: Monitor of {LOOP_SINK}")
        except Exception as e:
            self.log(f"wtf error: {e}")
        finally:
            self.running = False
            GLib.idle_add(self.btn_start.set_sensitive, True)

if __name__ == "__main__":
    win = ChispeakerApp()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

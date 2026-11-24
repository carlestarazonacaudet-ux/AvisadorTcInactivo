"""AoE2 DE - Avisador de aldeanos v26. Solo captura píxeles; no altera el juego."""
from __future__ import annotations

import ctypes
import os
import copy
import tempfile
import json
import queue
import random
import re
import shutil
import sys
import wave
import math
import unicodedata
import difflib
from tkinter import colorchooser, filedialog
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
from PIL import Image, ImageDraw, ImageOps, ImageSequence, ImageTk

import cv2
import mss
import numpy as np
import pygame
import pytesseract

PARCHMENT = '#EFDFBB'
PARCHMENT_LIGHT = '#F9EDCF'
PARCHMENT_PRESSED = '#D8BA7B'
GOLD_TEXT = '#674408'
GOLD_ACCENT = '#825910'
GOLD_BORDER = '#9F7428'
PANEL_BORDER = 4
HUD_TRANSPARENT = (1, 2, 3)
HUD_TEXTURES = {
    'madera_oscura': ('madera_oscura.png', '#222222'),
    'madera_rustica': ('madera_rustica.png', '#604733'),
}


def hud_colors(settings):
    texture = HUD_TEXTURES.get(settings.get('marco_fondo', HUD_APPEARANCE['marco_fondo']))
    background = texture[1] if texture else settings.get('marco_color_fondo', HUD_APPEARANCE['marco_color_fondo'])
    return background, settings.get('marco_color_letras', HUD_APPEARANCE['marco_color_letras'])


def picture_frame(paper, thickness, style='madera_tallada'):
    """Conserva las esquinas a inglete y estira solo los cuatro lados."""
    with Image.open(BASE / 'marco_dorado.png') as asset:
        frame = asset.convert('RGB')
    if style == 'madera_dorada':
        tones = ('#2F1D0E', '#E9C07B', '#946332')
    else:
        tones = ('#1B100B', '#B38151', '#593723')
    frame = ImageOps.colorize(ImageOps.grayscale(frame), *tones)
    with Image.open(BASE / 'madera_rustica.png') as wood:
        grain = ImageOps.fit(wood.convert('L'), frame.size, Image.Resampling.LANCZOS)
    grain = ImageOps.colorize(grain, '#28180E', '#C3925F')
    frame = Image.blend(frame, grain, 0.22)
    xs = (16, 46, 369, 399)
    ys = (15, 44, 337, 366)
    width, height = paper.size
    edge = min(thickness, width // 2, height // 2)
    dx = (0, edge, width - edge, width)
    dy = (0, edge, height - edge, height)
    for row in range(3):
        for col in range(3):
            if row == col == 1:
                continue
            size = dx[col + 1] - dx[col], dy[row + 1] - dy[row]
            if min(size) > 0:
                tile = frame.crop((xs[col], ys[row], xs[col + 1], ys[row + 1]))
                paper.paste(tile.resize(size, Image.Resampling.LANCZOS), (dx[col], dy[row]))



def parchment_panel(parent, *, vine_row=None, appearance=None, **options):
    """Marco dorado con grano de papel y bordes envejecidos."""
    border = int(options.get('highlightthickness', 0))
    vines = ()
    if vine_row is not None:
        with Image.open(BASE / 'esquina_enredadera.png') as asset:
            tile_width, tile_height = asset.width // 2, asset.height // 5
            top = vine_row * tile_height
            vines = tuple(asset.crop((x, top, x + tile_width, top + tile_height)).convert('RGBA')
                          for x in (0, tile_width))
        padding = {axis: options.pop(axis, 0) for axis in ('padx', 'pady')}
    background = hud_colors(appearance)[0] if appearance is not None else PARCHMENT
    texture = None
    if appearance is not None:
        texture_info = HUD_TEXTURES.get(appearance.get('marco_fondo', HUD_APPEARANCE['marco_fondo']))
        if texture_info:
            with Image.open(BASE / texture_info[0]) as asset:
                texture = asset.convert('RGB')
    frame = tk.Frame(parent, bg=background, **options)
    overhang = (22, 18) if vines and appearance is not None and os.name == 'nt' else (0, 0)
    frame.hud_overhang = overhang != (0, 0)
    backdrop = tk.Label(frame, bd=0, highlightthickness=0, bg=background)
    inset = 0 if vines else border + int(frame.cget('borderwidth'))
    backdrop.place(x=inset, y=inset, relwidth=1, relheight=1,
                   width=-2 * inset, height=-2 * inset, bordermode='ignore')
    backdrop.lower()
    if vines:
        frame.hud_painters = {}
        frame.content = hud_group(frame, bg=background, **padding) if appearance is not None else parchment_panel(frame, **padding)
        top_gap = round({1: 17, 2: 18, 3: 10}.get(vine_row, 30) * border / PANEL_BORDER)
        frame.content.pack(fill='both', expand=True, padx=7 + overhang[0],
                           pady=(top_gap + overhang[1], 7 + overhang[1]))

    def draw_paper(event):
        if event.width < 2 or event.height < 2:
            return
        width, height = event.width - 2 * inset, event.height - 2 * inset
        if width < 2 or height < 2:
            return
        margin_x, margin_y = overhang
        inner_size = width - 2 * margin_x, height - 2 * margin_y
        if min(inner_size) < 2:
            return
        if texture is not None:
            paper = ImageOps.fit(texture, inner_size, Image.Resampling.LANCZOS)
        elif appearance is not None:
            paper = Image.new('RGB', inner_size, background)
        else:
            rng = np.random.default_rng(26)
            clouds = Image.fromarray(rng.integers(70, 186, (8, 12), dtype=np.uint8))
            grain = np.asarray(clouds.resize((width, height), Image.Resampling.BICUBIC), dtype=float)
            grain = (grain - 128) * 0.20 + rng.normal(0, 1.7, grain.shape)
            x = np.minimum(np.arange(width), np.arange(width)[::-1])
            y = np.minimum(np.arange(height), np.arange(height)[::-1])
            shade = 16 * np.exp(-np.minimum(x[None, :], y[:, None]) / 13)
            pixels = np.array([239, 223, 187]) + (grain - shade)[..., None]
            paper = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
        if vines:
            style = (appearance or HUD_APPEARANCE).get('marco_estilo', HUD_APPEARANCE['marco_estilo'])
            picture_frame(paper, max(8, round(11 * border / PANEL_BORDER)), style)
            if frame.hud_overhang:
                interior = paper
                paper = Image.new('RGB', (width, height), HUD_TRANSPARENT)
                paper.paste(interior, overhang)
            vine_width = max(1, min(round(146 * border / PANEL_BORDER), width * 47 // 100))
            vine_height = min(height, max(1, round(vine_width * tile_height / tile_width)))
            for vine, x in zip(vines, (0, width - vine_width)):
                ornament = vine.resize((vine_width, vine_height), Image.Resampling.LANCZOS)
                if frame.hud_overhang and os.name == 'nt':
                    # No mezclar con el color clave: evita un halo en el borde exterior.
                    mask = ornament.getchannel('A').point(lambda alpha: 255 if alpha >= 112 else 0)
                else:
                    mask = ornament.getchannel('A')
                paper.paste(ornament, (x, 0), mask)
        frame.paper_surface = paper
        backdrop.paper = ImageTk.PhotoImage(paper, master=frame)
        backdrop.configure(image=backdrop.paper)
        if vines and appearance is not None:
            for paint in tuple(frame.hud_painters.values()):
                paint()

    frame.bind('<Configure>', draw_paper, add='+')
    return frame


def paint_on_hud(widget, render):
    """Pinta sobre el recorte exacto del fondo situado debajo del widget."""
    panel = widget.master
    while not hasattr(panel, 'hud_painters'):
        if panel.master is None or isinstance(panel, tk.Toplevel):
            return
        panel = panel.master

    def paint(_event=None):
        paper = getattr(panel, 'paper_surface', None)
        width, height = widget.winfo_width(), widget.winfo_height()
        if paper is None or width < 2 or height < 2:
            return
        x = widget.winfo_rootx() - panel.winfo_rootx()
        y = widget.winfo_rooty() - panel.winfo_rooty()
        render(paper.crop((x, y, x + width, y + height)))

    panel.hud_painters[widget] = paint
    widget.bind('<Configure>', paint, add='+')
    widget.bind('<Map>', paint, add='+')
    widget.bind('<Destroy>', lambda _event: panel.hud_painters.pop(widget, None), add='+')
    return paint


def hud_group(parent, **options):
    group = tk.Frame(parent, **options)
    backing = tk.Label(group, bd=0, highlightthickness=0)
    backing.place(x=0, y=0, relwidth=1, relheight=1, bordermode='ignore')
    backing.lower()

    def render(paper):
        backing.photo = ImageTk.PhotoImage(paper, master=backing)
        backing.configure(image=backing.photo)

    paint_on_hud(group, render)
    return group


class HudLabel(tk.Label):
    """Etiqueta con fondo continuo e imagen RGBA opcional."""
    def __init__(self, parent, *, art=None, **options):
        self.art = art
        self._paint = None
        if art is not None:
            self._size_image = tk.PhotoImage(master=parent, width=art.width, height=art.height)
            options['image'] = self._size_image
        super().__init__(parent, **options)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, takefocus=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1, bordermode='ignore')
        self._paint = paint_on_hud(self, self._render)

    def _render(self, paper):
        width, height = paper.size
        if self.art is not None:
            x, y = (width - self.art.width) // 2, (height - self.art.height) // 2
            paper.paste(self.art, (x, y), self.art)
        self.canvas.photo = ImageTk.PhotoImage(paper, master=self.canvas)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.canvas.photo, anchor='nw')
        anchor = self.cget('anchor')
        left = anchor.endswith('w')
        right = anchor.endswith('e') and anchor != 'center'
        x = 2 if left else width - 2 if right else width // 2
        self.canvas.create_text(x, height // 2, text=self.cget('text'), fill=self.cget('fg'),
                                font=self.cget('font'), tags='caption',
                                width=self.winfo_pixels(self.cget('wraplength')),
                                anchor='w' if left else 'e' if right else 'center')

    def configure(self, cnf=None, **options):
        result = super().configure(cnf, **options)
        if (options or isinstance(cnf, dict)) and self._paint is not None:
            self._paint()
        return result

    config = configure


class PulsingHudLabel(HudLabel):
    def __init__(self, parent, *, size, color, **options):
        self.base_size = size
        self.peak_size = round(size * 1.5)
        self.ink = color
        self.job = None
        self.start_time = 0
        font = Font(root=parent, family='Segoe UI', size=size, weight='bold')
        self.pulse_font = font
        super().__init__(parent, fg=color, font=('Segoe UI', self.peak_size, 'bold'),
                         **options)
        self.bind('<Map>', self._start, add='+')
        self.bind('<Unmap>', self._stop, add='+')
        self.bind('<Destroy>', self._stop, add='+')

    def _render(self, paper):
        super()._render(paper)
        self._apply_pulse()

    def _start(self, _event):
        if self.job is None:
            self.start_time = time.monotonic()
            self._tick()

    def _stop(self, _event):
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None

    def _apply_pulse(self):
        elapsed = time.monotonic() - self.start_time if self.start_time else 0
        pulse = (1 - math.cos(2 * math.pi * elapsed / 1.15)) / 2
        self.pulse_font.configure(size=round(self.base_size + (self.peak_size - self.base_size) * pulse))
        rgb = (round(value / 257 + (255 - value / 257) * .65 * pulse)
               for value in self.winfo_rgb(self.ink))
        shade = '#{:02x}{:02x}{:02x}'.format(*rgb)
        self.canvas.itemconfigure('caption', font=self.pulse_font, fill=shade)

    def _tick(self):
        self._apply_pulse()
        self.job = self.after(40, self._tick)


def apply_parchment_theme(root):
    root.configure(bg=PARCHMENT)
    style = ttk.Style(root)
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    style.configure('.', background=PARCHMENT, foreground=GOLD_TEXT,
                    bordercolor=GOLD_BORDER, lightcolor=GOLD_BORDER, darkcolor=GOLD_BORDER,
                    fieldbackground=PARCHMENT_LIGHT, selectforeground=GOLD_TEXT,
                    selectbackground=PARCHMENT_PRESSED, troughcolor=PARCHMENT_LIGHT,
                    insertcolor=GOLD_TEXT, arrowcolor=GOLD_TEXT, focuscolor=GOLD_ACCENT)
    style.configure('TLabelframe', relief='solid', borderwidth=2)
    style.configure('TNotebook', borderwidth=2)
    style.map('TNotebook.Tab', background=[('selected', PARCHMENT_LIGHT)])
    style.map('TButton', background=[('pressed', PARCHMENT_PRESSED),
                                     ('active', PARCHMENT_LIGHT)],
              foreground=[('disabled', GOLD_ACCENT)])
    style.map('TCombobox', fieldbackground=[('readonly', PARCHMENT_LIGHT)],
              foreground=[('readonly', GOLD_TEXT)])
    for control in ('TCheckbutton', 'TRadiobutton'):
        style.map(control, indicatorcolor=[('selected', GOLD_BORDER),
                                           ('!selected', PARCHMENT_LIGHT)])


BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PROGRAM_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
# Configuración persistente fuera de la carpeta de instalación: sobrevive actualizaciones.
DATA_DIR = Path(os.environ.get('LOCALAPPDATA') or str(Path.home())) / 'AoE2Avisador'
CFG_FILE = DATA_DIR / 'configuracion.json'
AGE_CURRENT_FILE = DATA_DIR / 'idle_edades_partida_actual.json'
AGE_HISTORY_FILE = DATA_DIR / 'historial_idle_edades.jsonl'
LEGACY_CONFIGS = [PROGRAM_DIR / f'configuracion_v{i}.json' for i in (7, 6, 5, 4, 3)]
ZONE_KEYS = ('zonas', 'zona_tiempo', 'zona_aldeanos', 'zona_pausa', 'zona_edad', 'zona_edad_texto', 'zona_rojo', 'rojo_ratio_ref', 'monitor', 'modo', 'modo_calibrado')
TEMPLATE_FILE = DATA_DIR / 'plantilla_aldeano_v4.png'  # writable en EXE onefile
LEGACY_TEMPLATE = PROGRAM_DIR / 'plantilla_aldeano_v4.png'
PAUSE_TEMPLATE = DATA_DIR / 'plantilla_pausa_v15.png'
RUNNING_TEMPLATE = DATA_DIR / 'plantilla_reanudada_v15.png'
DEFAULTS = {
    'marco_fondo': 'madera_oscura',
    'marco_color_fondo': '#26231E',
    'marco_color_letras': '#F0CE75',
    'marco_estilo': 'madera_tallada',
    'modo': 'global', 'espera': 3.0, 'repeticion': 6.0, 'intervalo': 0.18,
    'umbral': 0.58, 'monitor': 1, 'zonas': [], 'solo_juego_activo': True,
    'voz': 'Crea aldeanos', 'escalas': [0.85, 0.95, 1.0, 1.05, 1.15],
    'sonido': 'voz', 'archivo_sonido': '', 'volumen': 70,
    'limite_tiempo_activo': False, 'limite_minutos': 35,
    'limite_aldeanos_activo': False, 'limite_aldeanos': 130,
    'zona_tiempo': None, 'zona_aldeanos': None,
    'canal_aviso': 'ambos', 'imagen_visual': '', 'visual_tamano': 260,
    'visual_escala': 100, 'idle_total_escala': 100,
    'edades_escala': 100, 'controles_escala': 100,
    'visual_alerta_grande': True,
    'visual_esquina': 'inferior_derecha', 'visual_opacidad': 95,
    'visual_monitor': 1,
    'visual_posicion_libre': False, 'visual_pos_x': 80, 'visual_pos_y': 75,
    'mostrar_perdidas': True, 'segundos_aldeano': 25,
    'reiniciar_al_reloj_cero': True,
    'idle_total_visible': False, 'idle_total_monitor': 1,
    'idle_total_pos_x': 50, 'idle_total_pos_y': 5,
    'idle_total_opacidad': 94,
    'ocr_intervalo': 0.38, 'visual_permanencia': 2,
    'filtro_parpadeo_segundos': 1,
    'zona_pausa': None, 'zona_edad': None, 'zona_edad_texto': None, 'version_detector_edad': 26,
    'controles_visible': True, 'controles_monitor': 1,
    'controles_pos_x': 70, 'controles_pos_y': 3, 'controles_opacidad': 96,
    'rojo_activo': True, 'zona_rojo': None, 'rojo_ratio_ref': 0.0,
    'tecnologias_activo': True, 'mostrar_aviso_visual': True,
    'objetivos_idle': {},
}
HUD_APPEARANCE = {key: value for key, value in DEFAULTS.items() if key.startswith('marco_')}
BUILTIN_ALERTS = {'no_puede_ser': ('No puede ser', 'no puede ser.mp3'),
                  'espabila': ('Espabila', 'espabila.mp3')}
GOAL_PORTRAIT = 'felicitacion_age.png'
GOAL_SOUNDS = ('nacho partida de nivel.mp3', 'nacho digno de top player.mp3')
GOAL_BANNERS = (
    'MVP !!',
    'Ni yo lo haría mejor',
    'De clase mundial',
    'Tu ELO subirá como la espuma',
    'FU !!',
    'Eres el Vaipa',
    'Ni Jerardo',
)
MISSED_GOAL_BANNER = 'Mi abuelita se las arregla mucho mejor...'
MISSED_GOAL_COLOR = '#FF6565'
MISSED_GOAL_SOUND = 'abuelit.mp3'
GOAL_DURATION_MS = 7000


def audio_repeat_due(game_clock, previous_alert_clock, repeat_seconds):
    """Determina la repetición SOLAMENTE a partir del reloj del juego."""
    if game_clock is None:
        return False
    return (previous_alert_clock is None or game_clock < previous_alert_clock or
            game_clock - previous_alert_clock >= repeat_seconds)


def scaled_font(base, percent, minimum=7):
    """Escala la tipografía de los overlays manteniendo su legibilidad."""
    return max(minimum, round(base * max(50, min(200, int(percent))) / 100))


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def is_game_active():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        size = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(size + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, size + 1)
        title = buf.value.lower()
        return ('age of empires ii' in title or 'age of empires 2' in title
                or 'aoe2de' in title)
    except Exception:
        return False


def grab_monitor(sct, monitor_id):
    mon = sct.monitors[monitor_id]
    frame = np.asarray(sct.grab(mon))
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def choose_rect(title, image):
    rect = cv2.selectROI(title, image, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(title)
    rect = [int(v) for v in rect]
    if rect[2] < 12 or rect[3] < 12:
        raise ValueError('Selección cancelada o demasiado pequeña.')
    return rect


BUILTIN_DIR = BASE / 'templates_builtin'
TECH_DIR = BASE / 'tech_templates'


def load_templates():
    """Modelos hombre/mujer y progreso, incluidas las seis muestras aportadas."""
    paths = sorted(BUILTIN_DIR.glob('*.png'))
    if TEMPLATE_FILE.exists():
        paths.append(TEMPLATE_FILE)
    elif LEGACY_TEMPLATE.exists():
        paths.append(LEGACY_TEMPLATE)
    templates = []
    for path in paths:
        src = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if src is not None and min(src.shape[:2]) >= 12:
            templates.append((path.name, src))
    return templates



def load_technology_templates():
    """Tecnologías (capturas + iconos originales escalados a la cola de producción)."""
    models = []
    for path in sorted(TECH_DIR.glob('*.png')):
        src = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if src is not None and min(src.shape[:2]) >= 12:
            models.append((path.name, src))
    return models


def choose_production_kind(villager_score, technology_score, village_threshold=0.58,
                           technology_threshold=0.72, required_margin=0.045):
    """Clasifica un icono. La tecnología evita IDLE como un aldeano produciéndose.

    Cuando un icono es casi todo verde, los dos grupos pueden dar similitudes
    elevadas. Se exige un margen sobre el grupo de aldeanos para no confundir
    el progreso de un aldeano con una tecnología.
    """
    if (technology_score >= technology_threshold and
            technology_score >= villager_score + required_margin):
        return 'tecnologia', True
    if villager_score >= village_threshold:
        return 'aldeano', True
    return 'vacio', False

def neutralize_green(img):
    """Sustituye verdes intensos por gris oscuro; evita que el progreso controle la coincidencia."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (32, 65, 35), (95, 255, 255)) > 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray[green] = 38
    return gray, green


def icon_similarity(candidate, reference):
    """Comparación de iconos del mismo tamaño, ignorando números y áreas verdes.

    Una muestra muy tapada por verde puede producir INCIERTO en lugar de un falso NO.
    """
    h, w = reference.shape[:2]
    if candidate.shape[:2] != (h, w):
        candidate = cv2.resize(candidate, (w, h), interpolation=cv2.INTER_AREA)
    a, ga = neutralize_green(candidate)
    b, gb = neutralize_green(reference)
    # La cantidad sobreimpresa (1, 2...) es ajena al personaje.
    yy, xx = np.indices((h, w))
    digit = (xx < w * .39) & (yy < h * .42)
    # El progreso verde puede tapar gran parte de la ilustración.
    valid = (~digit) & (~ga) & (~gb)
    green_union = np.count_nonzero(ga | gb)
    green_inter = np.count_nonzero(ga & gb)
    green_iou = green_inter / green_union if green_union else 0.0
    if np.count_nonzero(valid) < max(35, int(h*w*.08)):
        # Si ambas imágenes tienen prácticamente el mismo avance verde,
        # no descartamos el modelo por quedar poca ropa visible.
        if green_union >= h*w*.20 and green_iou >= .72:
            return min(.92, .58 + .40*green_iou)
        return None
    a = a[valid].astype(np.float32)
    b = b[valid].astype(np.float32)
    std_a, std_b = a.std(), b.std()
    if std_a < 7 or std_b < 7:
        if green_union >= h*w*.20 and green_iou >= .72:
            return min(.92, .58 + .40*green_iou)
        return 0.0
    corr = float(np.mean((a-a.mean())*(b-b.mean())) / (std_a*std_b))
    # También comparamos la estructura aunque la ropa tenga distinta luminosidad.
    if green_union >= h*w*.20 and green_iou >= .50:
        corr = max(corr, .38 + .50 * green_iou)
    return max(-1.0, min(1.0, corr))


_MATCH_PREPARED_CACHE = {}


def prepared_queue_templates(templates, scales):
    """Genera modelos escalados una sola vez por monitorización.

    Antes se repetían 155 redimensiones/conversiones a HSV por fotograma,
    lo que producía un retraso perceptible en el contador.
    """
    key = (id(templates), tuple(scales))
    cached = _MATCH_PREPARED_CACHE.get(key)
    if cached is not None and cached[0] is templates:
        return cached[1]
    items = []
    for name, reference in templates:
        for scale in scales:
            th = max(8, round(reference.shape[0] * scale))
            tw = max(8, round(reference.shape[1] * scale))
            scaled = cv2.resize(reference, (tw, th),
                                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
            template_gray, template_green = neutralize_green(scaled)
            template_gray = cv2.GaussianBlur(template_gray,(3,3),0)
            items.append((name,scaled,template_gray,template_green))
    _MATCH_PREPARED_CACHE[key] = (templates, items)
    # Acota memoria de caché sin interferir con el worker en curso.
    if len(_MATCH_PREPARED_CACHE) > 8:
        for obsolete in list(_MATCH_PREPARED_CACHE)[:-4]:
            del _MATCH_PREPARED_CACHE[obsolete]
    return items


def mask_excluded_matches(response, width, height, excluded_boxes):
    """No puntuar candidatos cuyo centro cae dentro de un icono descartado."""
    for x, y, w, h in excluded_boxes:
        x1, y1 = max(0, x - width // 2), max(0, y - height // 2)
        x2, y2 = max(0, x + w - width // 2), max(0, y + h - height // 2)
        response[y1:y2, x1:x2] = -1


def load_fishing_ship_models(scales):
    with Image.open(BASE / 'FishingShipDE.webp') as image:
        icon = cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)
    # Los originales se normalizan a 46 px, como los de aldeanos y tecnologías.
    sizes = sorted({round(46 * scale) for scale in (*scales, .70, .78, .90, 1.10, 1.23, 1.32, 1.46)})
    models = []
    for size in sizes:
        scaled = cv2.resize(icon, (size, size), interpolation=cv2.INTER_AREA)
        edges = cv2.Sobel(scaled, cv2.CV_32F, 0, 1, ksize=3)[2:-2, 2:-2]
        variants = [edges]
        for progress in (.4, .65, .84):
            covered = round(progress * edges.shape[1])
            for columns in (slice(0, covered), slice(-covered, None)):
                tinted = edges.copy()
                tinted[:, columns] *= .28
                variants.append(tinted)
        models.append((size, variants))
    return models


def fishing_ship_boxes(region, models):
    """Localiza pesqueros por su silueta, aun con velo de progreso o bloqueo."""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    # La derivada vertical elimina el cambio de tono uniforme y evita los
    # bordes verticales que introduce una barra de progreso parcial.
    edges = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    green = green_progress_visible(region, min_fraction=.20)
    boxes = []
    for size, variants in models:
        extent = size - 4
        if extent > min(gray.shape):
            continue
        response = cv2.matchTemplate(edges, variants[0], cv2.TM_CCOEFF_NORMED)
        if green:
            for model in variants[1:]:
                result = cv2.matchTemplate(edges, model, cv2.TM_CCOEFF_NORMED)
                np.maximum(response, result, out=response)
        while True:
            _, score, _, (x, y) = cv2.minMaxLoc(response)
            if not np.isfinite(score) or score < .72:
                break
            box = (x - 2, y - 2, size, size)
            boxes.append(box)
            mask_excluded_matches(response, extent, extent, (box,))
    return boxes


def match_score(region, templates, scales, return_box=False, excluded_boxes=()):
    """Compara múltiples apariencias de aldeanos; devuelve (score, modelo, incierto).

    Desliza un modelo por la zona global. Si la región tiene el tamaño de un
    único icono, prueba igualmente las escalas de tamaño de la interfaz.
    """
    if region.size == 0:
        return -1.0, '', True
    rh, rw = region.shape[:2]
    best, best_name = -1.0, ''
    best_box = None
    uncertain = False
    # Primer pase rápido con coincidencia de bordes, ignorando saturación verde.
    reg_gray, reg_green = neutralize_green(region)
    reg_blur = cv2.GaussianBlur(reg_gray, (3, 3), 0)
    candidates = []
    for name, scaled, template_gray, template_green in prepared_queue_templates(templates,scales):
        th,tw=scaled.shape[:2]
        if th > rh or tw > rw:
            continue
        if template_gray.std() < 5:
            if template_green.std() < .10:
                continue
            match = cv2.matchTemplate(reg_green.astype(np.uint8), template_green.astype(np.uint8), cv2.TM_CCOEFF_NORMED)
        else:
            match = cv2.matchTemplate(reg_blur, template_gray, cv2.TM_CCOEFF_NORMED)
        if excluded_boxes:
            mask_excluded_matches(match, tw, th, excluded_boxes)
        k = min(5, match.size)
        flat = match.ravel()
        top = np.argpartition(flat, -k)[-k:]
        for idx in top:
            if flat[idx] <= -1:
                continue
            y, x = np.unravel_index(int(idx), match.shape)
            candidates.append((float(flat[idx]), name, scaled, x, y))
    if not candidates:
        return 0.0, '', False
    # Incluimos las más plausibles de cada plantilla; la puntuación final
    # utiliza solamente píxeles no afectados por la barra verde ni por el dígito.
    candidates.sort(key=lambda item: item[0], reverse=True)
    for rough, name, ref, x, y in candidates[:24]:
        hh, ww = ref.shape[:2]
        patch = region[y:y+hh, x:x+ww]
        # CONFIRMACIÓN ESTRUCTURAL: los mapas de césped pueden coincidir con
        # máscaras HSV verdes; exigimos que la ilustración real del icono
        # coincida también ANTES de neutralizar los colores. Esta correlación
        # se mantiene elevada para velos verdes translúcidos, incluso al 100 %.
        original_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
        if original_gray.std() < 3.0 or ref_gray.std() < 3.0:
            continue
        structure = float(cv2.matchTemplate(original_gray, ref_gray,
                                             cv2.TM_CCOEFF_NORMED)[0, 0])
        if not np.isfinite(structure) or structure < .50:
            continue
        value = icon_similarity(patch, ref)
        if value is None:
            # En una superposición muy intensa puede quedar tan poco del
            # retrato sin teñir que la comparación HSV sea indeterminada.
            # En ese caso aceptamos sólo una identidad estructural muy alta.
            if structure < .83:
                uncertain = True
                continue
            value = structure
        # La estructura, y no el porcentaje verde, fundamenta la detección.
        score = .62 * value + .30 * structure + .08 * rough
        if score > best:
            best, best_name = score, name
            best_box = (x, y, ww, hh)
    result = ((0.0 if best < 0 else best), best_name,
              uncertain and best < 0.35 and np.std(reg_gray) >= 7)
    return result + (best_box,) if return_box else result


def red_overlay_on_icon(image):
    """Detecta tinte rojo generalizado (TC BLOQUEADO), NO arte rojo del icono.

    Una tecnología como Carretilla o el escudo Feudal tiene rojo natural.
    Por eso no basta contar píxeles rojos: exigimos dominio del canal rojo
    frente al verde en prácticamente todo el icono.
    """
    if image is None or image.size == 0:
        return False
    height, width = image.shape[:2]
    if height < 15 or width < 15:
        return False
    # Interior: excluye marco de la cola y dígitos superiores a la izquierda.
    inner = image[max(1, int(height * .13)):max(2, int(height * .89)),
                  max(1, int(width * .12)):max(2, int(width * .88))]
    if inner.size == 0:
        return False
    blue, green, red = (ch.astype(np.float32) for ch in cv2.split(inner))
    bright = (red > 48) & ((red + green + blue) > 65)
    tinted = bright & (red > 2.0 * (green + 3)) & (red > 1.7 * (blue + 3))
    # Los retratos normales rojizos no se confunden con el velo rojo global.
    dominance = float(red.mean()) / max(1., float(green.mean()))
    return dominance >= 2.15 and float(tinted.mean()) >= .15


def green_progress_visible(region, min_fraction=.55):
    """Señal auxiliar de verde, NUNCA prueba suficiente de producción.

    El escenario puede ser íntegramente verde. Este valor sólo permite
    iniciar una búsqueda más costosa de una ilustración bajo el velo.
    """
    if region.size == 0:
        return False
    h,w=region.shape[:2]
    if h < 25 or w < 25:
        return False
    hsv=cv2.cvtColor(region,cv2.COLOR_BGR2HSV)
    green=(cv2.inRange(hsv,(35,67,32),(90,255,255))>0).astype(np.float32)
    if h < 80 and w < 80:
        return bool(np.mean(green) >= min_fraction)
    side=min(39,h,w)
    coverage=cv2.boxFilter(green,-1,(side,side),normalize=True,
                           borderType=cv2.BORDER_CONSTANT)
    return bool(np.max(coverage) >= min_fraction)


def match_green_icon_structure(region, villagers, technologies, scales, threshold=.68,
                               excluded_boxes=()):
    """Reconoce el ICONO DEBAJO del progreso verde (no el terreno).

    Un velo verde uniforme sobre un icono translúcido conserva la estructura
    en luminancia. CCOEFF_NORMED es invariante frente a una transformación
    afín de brillo (p.ej. 28% icono + 72% verde), pero no se activa por
    superficies de césped o cuadrículas que carezcan de la silueta.

    Si el icono está totalmente oculto por pintura verde opaca, no es
    posible inferir su identidad únicamente a partir de los píxeles: en
    tal caso la función no inventa una coincidencia.
    """
    if not green_progress_visible(region):
        return None
    gray=cv2.cvtColor(region,cv2.COLOR_BGR2GRAY)
    rh,rw=gray.shape[:2]
    best=None
    for kind, models in (('aldeano',villagers),('tecnologia',technologies)):
        for name, scaled, _, _ in prepared_queue_templates(models,scales):
            th,tw=scaled.shape[:2]
            if th>rh or tw>rw:
                continue
            ref_gray=cv2.cvtColor(scaled,cv2.COLOR_BGR2GRAY)
            if ref_gray.std()<4:
                continue
            result=cv2.matchTemplate(gray,ref_gray,cv2.TM_CCOEFF_NORMED)
            if excluded_boxes:
                mask_excluded_matches(result, tw, th, excluded_boxes)
            _, score, _, (x,y)=cv2.minMaxLoc(result)
            if score < threshold or not np.isfinite(score):
                continue
            patch=region[y:y+th,x:x+tw]
            # El color rojo sobre el icono prevalece sobre una coincidencia
            # de la silueta (ya no produce aldeanos ni tecnologías).
            if red_overlay_on_icon(patch):
                continue
            if best is None or score>best[0]:
                best=(float(score),kind,name)
    return best


def classify_queue_region(region, villagers, technologies, scales, village_threshold=.58,
                          technology_threshold=.60, fishing_models=()):
    """Devuelve (ocupado, estado, puntuación) en la cola calibrada.

    Cualquier icono SIN velo rojo es actividad válida. Iconos cubiertos de
    verde siguen siendo actividad; rojo / cola vacía suman IDLE.
    En colas globales puede haber simultáneamente un icono rojo y otro
    investigándose. El rojo no anula al otro: examinamos las coincidencias
    restantes antes de decidir el estado global.
    """
    if region.size == 0:
        return False, 'sin imagen', 0.
    height,width = region.shape[:2]
    excluded = fishing_ship_boxes(region, fishing_models) if fishing_models else ()
    if max(height,width) <= 100 and red_overlay_on_icon(region):
        return False, 'bloqueado rojo', 1.

    # Nunca declarar actividad por verde SIN confirmar un icono: el césped
    # del mapa activa esa condición con mucha frecuencia. El segundo paso
    # comprueba que debajo haya una de las ilustraciones suministradas.
    green_match = match_green_icon_structure(region, villagers, technologies, scales,
                                            excluded_boxes=excluded)
    if green_match is not None:
        score, kind, name = green_match
        return True, f'{kind} con progreso verde ({name})', score

    working=region.copy()
    last_red=None
    last_score=0.
    passes = 4 if max(width,height)>100 else 1
    for _ in range(passes):
        v_score,v_name,_,v_rect = match_score(working, villagers, scales, return_box=True,
                                             excluded_boxes=excluded)
        t_score,t_name,_,t_rect = (match_score(working, technologies, scales, return_box=True,
                                              excluded_boxes=excluded)
                                   if technologies else (0.,'',False,None))
        last_score=max(last_score,v_score,t_score)
        outcomes=[]
        for kind,score,name,rect,cutoff in (
                ('aldeano',v_score,v_name,v_rect,village_threshold),
                ('tecnologia',t_score,t_name,t_rect,technology_threshold)):
            if rect is None or score < cutoff:
                continue
            x,y,ww,hh=rect
            patch=working[y:y+hh,x:x+ww]
            if red_overlay_on_icon(patch):
                outcomes.append((False,'bloqueado rojo ('+name+')',score,rect))
            else:
                outcomes.append((True,kind+' ('+name+')',score,rect))
        active=[record for record in outcomes if record[0]]
        if active:
            found=max(active,key=lambda record:record[2])
            return found[:3]
        red=[record for record in outcomes if not record[0]]
        if red:
            last_red=max(red,key=lambda record:record[2])
        if not red or passes == 1:
            break
        # El rojo se elimina SOLO en la copia de trabajo, para comprobar si
        # quedan otras producciones visibles en una cola global multícono.
        for _,_,_,(x,y,ww,hh) in red:
            working[y:y+hh,x:x+ww] = 0
    if last_red is not None:
        return last_red[:3]
    if excluded:
        return False, 'pesquero excluido de la cola del TC', last_score
    return False, 'cola vacía / no reconocida', last_score


def red_coverage(region):
    """Ratio de píxeles rojo intenso dentro de la zona del icono calibrado.

    No se aplica al HUD completo: las decoraciones rojas de AoE2 generarían
    falsos positivos. El usuario selecciona un icono rojo concreto.
    """
    if region is None or region.size == 0 or region.shape[0] < 8 or region.shape[1] < 8:
        return 0.0
    # Ignora el borde exterior para no confundir el marco rojizo del HUD.
    h,w=region.shape[:2]
    inner=region[max(1,h//18):h-max(1,h//18), max(1,w//18):w-max(1,w//18)]
    if inner.size == 0:
        return 0.0
    hsv=cv2.cvtColor(inner,cv2.COLOR_BGR2HSV)
    hue,sat,val=cv2.split(hsv)
    pixels=(((hue<=12)|(hue>=172)) & (sat>=115) & (val>=80))
    return float(np.count_nonzero(pixels))/pixels.size


def red_idle_detected(region, calibration_ratio=0.0):
    """Rojo observado por encima del umbral de referencia de calibración.

    Se exige >=4 % de rojo saturado y al menos el 48 % del porcentaje de
    referencia; el avance verde no se considera rojo.
    """
    frac=red_coverage(region)
    return frac >= max(.04, float(calibration_ratio)*.48)


def rect_overlap(one, two):
    ax,ay,aw,ah=one
    bx,by,bw,bh=two
    return max(0,min(ax+aw,bx+bw)-max(ax,bx))*max(0,min(ay+ah,by+bh)-max(ay,by))


class AlarmLogic:
    """Estado de cada indicador; solo hay alarma con evidencia negativa continua."""
    def __init__(self, wait_seconds=3):
        self.wait_seconds = wait_seconds
        self.missing_since = {}

    def clear(self):
        self.missing_since.clear()

    def evaluate(self, observations, now):
        # observations: lista (name, True|False|None). None = lectura inválida.
        if not observations or any(value is None for _, value in observations):
            self.clear()
            return 'INCIERTO', []
        inactive = []
        for name, value in observations:
            if value:
                self.missing_since.pop(name, None)
            else:
                self.missing_since.setdefault(name, now)
                if now - self.missing_since[name] >= self.wait_seconds:
                    inactive.append(name)
        return ('ALERTA' if inactive else 'NORMAL'), inactive


def find_tesseract():
    bundled = BASE / 'ocr' / 'tesseract.exe'
    candidates = [bundled if bundled.is_file() else None, shutil.which('tesseract'),
                  r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                  r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe']
    for path in candidates:
        if path and Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            if Path(path) == bundled:
                os.environ['TESSDATA_PREFIX'] = str(BASE / 'ocr' / 'tessdata')
            return True
    return False


def hud_ocr_variants(image):
    """Segmentación independiente del color (blanco, amarillo, cian o dorado).

    El texto claro suele quedar sobre un HUD oscuro. Los filtros HSV no
    presuponen que las cifras sean blancas ni dependen del fondo del juego.
    """
    if image is None or image.size == 0:
        return []
    bgr = image[:, :, :3]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, saturation, value = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Cian/azul brillante, amarillo/dorado y blanco neutro.
    cool = cv2.inRange(hsv, (73, 35, 115), (110, 255, 255))
    warm = cv2.inRange(hsv, (10, 45, 110), (48, 255, 255))
    pale = cv2.inRange(hsv, (0, 0, 140), (179, 115, 255))
    light_text = cv2.bitwise_or(cv2.bitwise_or(cool, warm), pale)
    # Suprime artefactos pequeños sin erosionar los dos puntos del reloj.
    masks = [otsu, light_text]
    # Mantener el gris sin marco como primera prueba: los dos puntos finos
    # de AoE2 pueden transformarse en puntos extra por el padding.
    variants = [gray, enhanced, *masks]
    results = []
    for variant in variants:
        up = cv2.resize(variant, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        results.append(up)
    return results


def _parse_hud_clock(raw):
    """Interpreta una hora completa, sin aceptar horas reconstruidas por azar.

    Se permiten repeticiones de los dos puntos (artefacto de Tesseract), pero
    NO las cifras de velocidad, dificultad ni números del resto del HUD.
    """
    raw = re.sub(r'\s+', '', str(raw)).replace(';', ':').replace('；', ':')
    raw = re.sub(r':{2,}', ':', raw)
    found = re.search(r'(?<!\d)(\d{1,2}):(\d{2}):(\d{2})(?!\d)', raw)
    if found:
        hours, minutes, seconds = map(int, found.groups())
        if 0 <= hours <= 12 and minutes < 60 and seconds < 60:
            return hours * 3600 + minutes * 60 + seconds
    return None


def _clock_ocr_variants(image):
    """Masks para texto cian, blanco y amarillo sobre cualquier terreno.

    Importante: la región es la del RELOJ; los rótulos de la derecha se
    excluyen probando primero un ancho proporcional a la altura del HUD.
    """
    if image is None or image.size == 0:
        return []
    hsv = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    cyan = cv2.inRange(hsv, (73, 25, 100), (115, 255, 255))
    yellow = cv2.inRange(hsv, (10, 60, 120), (48, 255, 255))
    white = cv2.inRange(hsv, (0, 0, 155), (179, 105, 255))
    combined = cv2.bitwise_or(cyan, cv2.bitwise_or(yellow, white))
    # Primer intento: cian aislado (frecuente en AoE2: DE con césped verde).
    # Otros modos/fondos: segmentación de todos los colores de letras, gris.
    return [cyan, combined, gray]


def ocr_game_clock(image):
    """Lee el reloj sin confundir '(Normal - 1.7) (Extremo)' con la hora.

    Admite zona ajustada al reloj y zona ancha con leyendas de velocidad.
    Los recortes más estrechos se prueban primero cuando el usuario ha
    calibrado toda la franja superior. Una lectura fallida devuelve None.
    """
    if image is None or image.size == 0:
        return None
    h, w = image.shape[:2]
    if h < 6 or w < 15:
        return None
    # 00:07:30 ocupa aprox. 2.0–3.0 alturas de la franja capturada.
    # Si solo se ha seleccionado el reloj, NO recortamos sus dígitos.
    widths = []
    if w >= 3.4 * h:
        widths = [min(w, int(h * factor)) for factor in (2.4, 3.05, 3.8)]
    else:
        widths = [w]
    widths.append(w)
    widths = list(dict.fromkeys(max(15, value) for value in widths))
    # Las letras de AoE2 están en la parte superior de la ROI; en una selección
    # demasiado alta, el terreno bajo ellas empeora el contraste del OCR.
    for width in widths:
        region = image[:, :width]
        cropped = [region]
        if h >= 38:
            cropped.insert(0, region[:max(24, int(h * .73)), :])
        for candidate in cropped:
            for variant in _clock_ocr_variants(candidate):
                up = cv2.resize(variant, None, fx=3, fy=3,
                                interpolation=cv2.INTER_CUBIC)
                try:
                    raw = pytesseract.image_to_string(
                        up, config='--psm 7 -c tessedit_char_whitelist=0123456789:;')
                except Exception:
                    return None
                clock = _parse_hud_clock(raw)
                if clock is not None:
                    return clock
    return None


def ocr_digits(image, kind):
    """OCR para el reloj de juego (múltiples colores) o aldeanos del HUD."""
    if kind == 'tiempo':
        return ocr_game_clock(image)
    for pix in hud_ocr_variants(image):
        try:
            raw = pytesseract.image_to_string(
                pix, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        except Exception:
            return None
        numbers = re.findall(r'(?<!\d)\d{1,3}(?!\d)', raw)
        for text_number in numbers:
            value = int(text_number)
            if 0 <= value <= 300:
                return value
    return None


def ocr_hud_text(image):
    """OCR general opcional para diagnóstico de rótulos de cualquier color.

    La edad de la partida se identifica POR ESCUDO, no por este texto.
    """
    for pix in hud_ocr_variants(image):
        try:
            text = pytesseract.image_to_string(pix, config='--psm 7').strip()
            if sum(ch.isalpha() for ch in text) >= 4:
                return text
        except Exception:
            return ''
    return ''


class SoundEngine:
    """Reproduce WAV/MP3/pitidos y TTS de Windows por un único mixer con volumen."""
    def __init__(self, log):
        self.log = log
        self.jobs = queue.Queue(maxsize=2)
        self.running = True
        self.lock = threading.RLock()
        self.mixer_ok = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.celebration_channel = pygame.mixer.Channel(0)
            self.beep_channel = pygame.mixer.Channel(1)
            self.mixer_ok = True
        except Exception as exc:
            self.log('No se pudo iniciar el audio: ' + str(exc))
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def play(self, setting):
        try:
            self.jobs.put_nowait(setting.copy())
        except queue.Full:
            pass

    def stop_sound(self, *, include_celebration=False):
        with self.lock:
            if self.mixer_ok:
                pygame.mixer.music.stop()
                self.beep_channel.stop()
                if include_celebration:
                    self.celebration_channel.stop()
        while True:
            try:
                self.jobs.get_nowait()
            except queue.Empty:
                break

    def play_celebration(self, filename, volume):
        if not self.mixer_ok:
            return
        with self.lock:
            self.stop_sound()
            clip = pygame.mixer.Sound(str(BASE / 'sonidos' / filename))
            self.celebration_channel.set_volume(max(0, min(100, int(volume))) / 100)
            self.celebration_channel.play(clip)

    def loop(self):
        while self.running:
            try:
                setting = self.jobs.get(timeout=.2)
            except queue.Empty:
                continue
            if setting is None:
                break
            try:
                self._play(setting)
            except Exception as exc:
                self.log('Error de sonido: ' + str(exc))

    def _play(self, setting):
        if not self.mixer_ok:
            self.log('Audio no disponible: revisa el dispositivo de salida de Windows.')
            return
        mode = setting.get('sonido', 'voz')
        volume = max(0, min(100, int(setting.get('volumen', 70)))) / 100.0
        if mode == 'archivo' or mode in BUILTIN_ALERTS:
            if mode in BUILTIN_ALERTS:
                path = BASE / 'sonidos' / BUILTIN_ALERTS[mode][1]
            else:
                path = Path(setting.get('archivo_sonido', ''))
            if not path.is_file() or path.suffix.lower() not in ('.mp3', '.wav'):
                self.log('El MP3/WAV elegido no existe o no tiene formato compatible.')
                return
            self._music(str(path), volume)
        elif mode == 'voz':
            self._voice(setting.get('voz', 'Crea aldeanos'), volume)
        else:
            count = 2 if mode == 'doble' else 3
            self._beep(count, volume)

    def _music(self, path, volume):
        with self.lock:
            if self.celebration_channel.get_busy():
                return False
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
            return True

    def _beep(self, count, volume):
        sample_rate = 44100
        beep_length = .16
        silence = .13
        samples = []
        for _ in range(count):
            n = int(sample_rate * beep_length)
            for j in range(n):
                attack = min(1.0, j/400)
                release = min(1.0, (n-j)/500)
                samples.append(int(9000 * math.sin(2*math.pi*850*j/sample_rate) * attack * release))
            samples.extend([0] * int(sample_rate * silence))
        arr = np.asarray(samples, dtype=np.int16)
        stereo = np.column_stack([arr, arr])
        sound = pygame.sndarray.make_sound(np.ascontiguousarray(stereo))
        sound.set_volume(volume)
        with self.lock:
            if not self.celebration_channel.get_busy():
                self.beep_channel.play(sound)

    def _voice(self, phrase, volume):
        # System.Speech genera un WAV temporal; mixer aplica el volumen.
        # No requiere conexión a Internet ni instalaciones TTS de Python.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='aoe2_voz_') as directory:
            dest = Path(directory) / 'voz.wav'
            safe_phrase = phrase.replace("'", "''")
            safe_dest = str(dest).replace("'", "''")
            script = ("Add-Type -AssemblyName System.Speech; "
                      "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                      "$s.SetOutputToWaveFile('" + safe_dest + "'); "
                      "$s.Speak('" + safe_phrase + "'); $s.Dispose()")
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                           timeout=20, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if not self._music(str(dest), volume):
                return
            # Wait for completion so temporary audio is not removed mid-play.
            deadline = time.monotonic()+12
            while pygame.mixer.music.get_busy() and time.monotonic()<deadline and self.running:
                time.sleep(.06)
            pygame.mixer.music.stop()

    def close(self):
        self.running = False
        self.stop_sound(include_celebration=True)
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass



def format_game_duration(seconds):
    if seconds is None:
        return '--:--'
    seconds = max(0, int(seconds))
    return f'{seconds // 3600:02d}:{(seconds // 60) % 60:02d}:{seconds % 60:02d}' if seconds >= 3600 else f'{seconds // 60:02d}:{seconds % 60:02d}'



# V23: escudos aportados por el usuario, fondo excluido usando máscaras.
AGE_ORDER = ('oscura', 'feudal', 'castillos', 'imperial')
AGE_NAMES = {
    'oscura': 'Alta Edad Media (I)', 'feudal': 'Edad Feudal (II)',
    'castillos': 'Edad de los Castillos (III)', 'imperial': 'Edad Imperial (IV)',
}
AGE_IMAGES = BASE / 'age_shields'


def shield_alpha_mask(reference):
    """Máscara de SILUETA que conserva también números oscuros internos.

    Rellenamos el contorno exterior del escudo; el fondo negro ajeno a la
    insignia no participa. A diferencia de la V22, no eliminamos los píxeles
    oscuros INTERIORES, necesarios para discriminar los números I/II/III/IV.
    """
    if reference is None or reference.size == 0:
        return None
    if reference.ndim == 2:
        intensity=reference
    else:
        intensity=reference[:,:,:3].max(axis=2)
    seed=np.uint8(intensity > 22)*255
    seed=cv2.morphologyEx(seed,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    contours,_=cv2.findContours(seed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour=max(contours,key=cv2.contourArea)
    if cv2.contourArea(contour)<150:
        return None
    mask=np.zeros(seed.shape,dtype=np.uint8)
    cv2.drawContours(mask,[contour],-1,255,-1)
    # Reduce el halo/antialias de los extremos sin perder la forma.
    mask=cv2.erode(mask,np.ones((3,3),np.uint8),iterations=1)
    return mask if np.count_nonzero(mask)>=150 else None


def score_shield_at_scale(region, reference, mask):
    """Comparación SOLO sobre el escudo, no sobre el escenario exterior."""
    h,w=reference.shape[:2]
    if h>region.shape[0] or w>region.shape[1] or min(h,w)<13:
        return -1.0
    if mask is None or np.count_nonzero(mask)<80:
        return -1.0
    try:
        # Correlación centrada: evita atribuir altas puntuaciones a fondos claros
        # que no se corresponden con los detalles del numeral romano.
        response=cv2.matchTemplate(cv2.cvtColor(region,cv2.COLOR_BGR2GRAY),
                                   cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY),
                                   cv2.TM_CCORR_NORMED,mask=mask)
        valid=response[np.isfinite(response)]
        score=float(valid.max()) if valid.size else -1.0
    except cv2.error:
        return -1.0
    return score if np.isfinite(score) else -1.0


def load_age_signatures():
    """Carga las CUATRO referencias exactas y sus máscaras en PNG."""
    refs={}
    for name in AGE_ORDER:
        img=cv2.imread(str(AGE_IMAGES/f'{name}.png'),cv2.IMREAD_COLOR)
        supplied_mask=cv2.imread(str(AGE_IMAGES/f'{name}_mask.png'),cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        mask=(supplied_mask if supplied_mask is not None and
              supplied_mask.shape==img.shape[:2] else shield_alpha_mask(img))
        if mask is not None and np.count_nonzero(mask)>150:
            refs[name]=(img,mask)
    return refs


def age_shield_scores(region, signatures):
    """Puntuaciones independientes por edad, con margen y cambio de escala."""
    scores={}
    if region is None or region.size==0 or min(region.shape[:2])<14:
        return scores
    h,w=region.shape[:2]
    for name,(ref,mask) in signatures.items():
        base=min(w/ref.shape[1],h/ref.shape[0])
        best=-1.0
        for fraction in (.45,.50,.55,.60,.65,.70,.75,.80,.85,.90,.95,1.0):
            scale=base*fraction
            nw=max(1,round(ref.shape[1]*scale))
            nh=max(1,round(ref.shape[0]*scale))
            if min(nw,nh)<14 or nw>w or nh>h:
                continue
            img=cv2.resize(ref,(nw,nh),interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR)
            m=cv2.resize(mask,(nw,nh),interpolation=cv2.INTER_NEAREST)
            best=max(best,score_shield_at_scale(region,img,m))
        scores[name]=best
    return scores


def detect_game_age(region, signatures):
    scores=age_shield_scores(region,signatures)
    if len(scores)!=4:
        return None,0.0
    ranked=sorted(scores.items(),key=lambda item:item[1],reverse=True)
    first,second=ranked[:2]
    # Ambigüedad: no cambiar de edad si el mejor escudo no destaca claramente.
    if first[1]<.81 or first[1]-second[1]<.055:
        return None,first[1]
    return first

AGE_TEXT_HINTS = {
    'oscura': ('alta edad media', 'edad oscura'),
    'feudal': ('edad feudal', 'feudal'),
    'castillos': ('edad de los castillos', 'edad castillos'),
    'imperial': ('edad imperial', 'imperial'),
}


def _normalize_age_text(raw):
    text = unicodedata.normalize('NFKD', str(raw).lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z\s]', ' ', text)
    return ' '.join(text.split())


def identify_age_text(raw):
    """Reconoce edad desde texto (blanco, cian o amarillo), con margen.

    Devuelve (edad, confianza). Un texto insuficiente no confirma una edad.
    """
    cleaned = _normalize_age_text(raw)
    if len(cleaned) < 6:
        return None, 0.0
    ranking = []
    for age, expressions in AGE_TEXT_HINTS.items():
        scores = []
        for phrase in expressions:
            if phrase in cleaned:
                scores.append(1.0)
            else:
                scores.append(difflib.SequenceMatcher(None, cleaned, phrase).ratio())
        ranking.append((age, max(scores)))
    ranking.sort(key=lambda item: item[1], reverse=True)
    (age, confidence), (_, second) = ranking[:2]
    return (age, confidence) if confidence >= .76 and confidence - second >= .07 else (None, confidence)


def detect_game_age_text(image):
    """OCR de rótulo de edad en dos colores y sobre escenarios distintos.

    No exige tesseract en español: se usan letras ASCII y comparación difusa.
    """
    if image is None or image.size == 0:
        return None, 0.0
    gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2HSV)
    pale = cv2.inRange(hsv, (0, 0, 125), (179, 125, 255))
    yellow = cv2.inRange(hsv, (9, 45, 110), (47, 255, 255))
    text_mask = cv2.bitwise_or(pale, yellow)
    # Blanco/amarillo, pero también fondos oscuros y texto con halo negro.
    candidates = [gray, text_mask]
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    candidates.append(otsu)
    best = (None, 0.0)
    for pixels in candidates:
        up = cv2.resize(pixels, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        try:
            raw = pytesseract.image_to_string(up, config='--psm 7')
        except Exception:
            return None, 0.0
        result = identify_age_text(raw)
        if result[0] is not None:
            return result
        if result[1] > best[1]:
            best = result
    return best


def reconcile_age_observations(shield, text_age):
    """Fusiona ambas fuentes. Discrepancia = desconocido, nunca cambiar a ciegas."""
    if shield and text_age and shield != text_age:
        return None, 'CONFLICTO'
    if shield and text_age:
        return shield, 'ESCUDO + TEXTO'
    if shield:
        return shield, 'ESCUDO'
    if text_age:
        return text_age, 'TEXTO'
    return None, 'SIN LECTURA'


def store_age_snapshot(snapshot, clock_seconds, archive=False):
    """Registro persistente por partida. La hora civil solo identifica el archivo;
    ningún cálculo de IDLE depende de ella.
    """
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    record={'edades':snapshot,'reloj_partida_segundos':clock_seconds,
            'guardado':time.strftime('%Y-%m-%d %H:%M:%S')}
    if archive:
        if snapshot.get('total',0)>0:
            with AGE_HISTORY_FILE.open('a',encoding='utf-8') as handle:
                handle.write(json.dumps(record,ensure_ascii=False)+'\n')
        return
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',
             dir=DATA_DIR,delete=False,suffix='.tmp') as handle:
        json.dump(record,handle,ensure_ascii=False,indent=2)
        tmp=Path(handle.name)
    try:
        tmp.replace(AGE_CURRENT_FILE)
    finally:
        tmp.unlink(missing_ok=True)


class AgeIdleTracker:
    """Reparte el IDLE del ÚNICO reloj de juego entre las edades.

    Cada aldeano potencial no producido se contabiliza al cruzar un múltiplo
    de 25 s de IDLE acumulado. Se atribuye a la edad durante la que se alcanza
    ese múltiplo, con lo que la suma por edades + sin asignar coincide SIEMPRE
    con el total (incluso con residuos <25 s entre edades).
    """
    def __init__(self, cadence=25):
        self.cadence = max(1, int(cadence))
        self.reset()

    def reset(self):
        self.values = {age: 0 for age in AGE_ORDER}
        self.lost_by_age = {age: 0 for age in AGE_ORDER}
        self.seen = set()
        self.active = None
        self.previous_total = 0
        self.unassigned_lost = 0
        self.candidate = None
        self.candidate_reads = 0

    def observe(self, age, total, clock_valid=True):
        total = max(0, int(total))
        if total < self.previous_total:
            self.reset()
        delta = max(0, total-self.previous_total)
        newly_lost = total // self.cadence - self.previous_total // self.cadence
        if self.active is not None:
            self.values[self.active] += delta
            self.lost_by_age[self.active] += newly_lost
        else:
            self.unassigned_lost += newly_lost
        self.previous_total = total
        if age in AGE_ORDER and clock_valid:
            if age == self.candidate:
                self.candidate_reads += 1
            else:
                self.candidate, self.candidate_reads = age, 1
            if self.candidate_reads >= 2:
                if self.active is None or AGE_ORDER.index(age) >= AGE_ORDER.index(self.active):
                    self.active = age
                    self.seen.add(age)
                self.candidate = None
                self.candidate_reads = 0
        elif age is None:
            self.candidate = None
            self.candidate_reads = 0
        return self.snapshot()

    def snapshot(self):
        return {'age': self.active, 'values': dict(self.values),
                'lost_by_age': dict(self.lost_by_age),
                'seen': sorted(self.seen),
                'unassigned': max(0, self.previous_total-sum(self.values.values())),
                'unassigned_lost': self.unassigned_lost,
                'lost_total': self.previous_total // self.cadence,
                'total': self.previous_total}


class ClockSynchronizedIdle:
    """Única fuente de verdad para los dos HUD: SOLO segundos OCR del juego.

    Una lectura igual (partida pausada) aporta delta=0. Las lecturas erróneas
    no generan segundos imaginarios. El tiempo actual y el acumulado se miden
    con los MISMOS incrementos observados y aceptados.
    """
    def __init__(self, cadence=25):
        self.cadence = max(1, int(cadence))
        self.reset()

    def reset(self):
        self.total_seconds = 0
        self.running = {}
        self.previous_states = {}
        self.previous_clock = None
        self.current_clock = None
        self.valid_clock = False
        self.paused = False

    def reset_accumulated(self):
        self.total_seconds = 0

    def sample(self, observations, clock_read=False, game_seconds=None, paused=False):
        states = dict(observations)
        self.paused = bool(paused)
        # Cambios de estado se observan en cada captura (también entre dos OCR).
        for name, value in states.items():
            if value is True:
                self.running[name] = 0
            elif value is False:
                self.running.setdefault(name, 0)

        if paused:
            # Al reanudar descartamos el intervalo que contiene la pausa.
            self.previous_clock = None
            self.valid_clock = False
            self.previous_states = states
            return self.snapshot(states)

        if clock_read:
            if game_seconds is None:
                self.previous_clock = None
                self.valid_clock = False
                self.previous_states = states
                return self.snapshot(states)
            new_clock = int(game_seconds)
            if self.previous_clock is not None:
                delta = new_clock - self.previous_clock
                # OCR cada ~0.4 s. Los saltos mayores se tratan como pérdida
                # de seguimiento; NO se suman, aunque el número parezca válido.
                if 0 < delta <= 4:
                    for name, value in states.items():
                        if value is False and self.previous_states.get(name) is False:
                            self.running[name] = self.running.get(name, 0) + delta
                            self.total_seconds += delta
                elif delta < 0 or delta > 4:
                    # Nunca modificar un total en base a un reloj que retrocede.
                    self.previous_clock = None
                    self.valid_clock = False
                    self.previous_states = states
                    return self.snapshot(states)
            self.previous_clock = new_clock
            self.current_clock = new_clock
            self.valid_clock = True
        self.previous_states = states
        return self.snapshot(states)

    def snapshot(self, states):
        current = [self.running.get(n, 0) for n,v in states.items() if v is False]
        lost = sum(self.running.get(n, 0) // self.cadence for n,v in states.items() if v is False)
        return {'idle': max(current, default=0), 'lost': lost,
                'total': self.total_seconds, 'clock': self.current_clock,
                'clock_ok': self.valid_clock, 'paused': self.paused}


class ClockSynchronizedIdleFiltered(ClockSynchronizedIdle):
    """Mismo reloj OCR y mismas cifras, con confirmación de producción.

    Si el detector cree ver producción durante una inactividad, espera a que
    transcurra 1 segundo DE PARTIDA con lecturas persistentes. Mientras tanto,
    no borra el IDLE ni desactiva el aviso. Los segundos dudosos se reservan:
    * falso positivo: se reintegran completos al contador acumulado;
    * producción real: se descartan, equivalente a descontar el segundo de
      confirmación antes de publicar los totales (sin hacerlos retroceder).

    Esto evita que el desglose por edades pierda datos al recalcular el total.
    """
    def __init__(self, cadence=25, confirm_seconds=1):
        self.confirm_seconds = max(1, int(confirm_seconds))
        super().__init__(cadence)

    def reset(self):
        super().reset()
        self.confirmed = {}
        self.probes = {}  # nombre -> (reloj_inicio, segundos_reservados, lecturas)

    def reset_accumulated(self):
        super().reset_accumulated()
        # Conserva las inactividades en curso y el estado de prueba.

    def sample(self, observations, clock_read=False, game_seconds=None, paused=False):
        raw = dict(observations)
        self.paused = bool(paused)
        for name, value in raw.items():
            if name not in self.confirmed and value is not None:
                self.confirmed[name] = value
                if value is False:
                    self.running.setdefault(name, 0)

        if paused:
            self.probes.clear()
            self.previous_clock = None
            self.valid_clock = False
            self.previous_states = dict(self.confirmed)
            return self.snapshot(self.confirmed)

        if clock_read and game_seconds is None:
            # Un OCR ilegible no da tiempo nuevo; tampoco confirma producción.
            self.previous_clock = None
            self.valid_clock = False
            self.previous_states = dict(self.confirmed)
            return self.snapshot(self.confirmed)

        valid_time = int(game_seconds) if clock_read and game_seconds is not None else self.current_clock
        delta = 0
        if clock_read:
            if self.previous_clock is not None:
                delta = int(game_seconds) - self.previous_clock
                if delta < 0 or delta > 4:
                    self.previous_clock = None
                    self.valid_clock = False
                    self.probes.clear()
                    self.previous_states = dict(self.confirmed)
                    return self.snapshot(self.confirmed)
            self.previous_clock = int(game_seconds)
            self.current_clock = int(game_seconds)
            self.valid_clock = True
            delta = max(0, delta)

        for name, value in raw.items():
            was = self.confirmed.get(name)
            if value is None:
                # Lectura incierta: no eliminar el estado anterior ni fabricar
                # segundos que no se puedan asignar con seguridad.
                continue
            if was is True and value is False:
                self.confirmed[name] = False
                self.running[name] = 0
                self.probes.pop(name, None)
            elif was is False and value is True:
                probe = self.probes.get(name)
                if probe is None:
                    # Si la primera lectura positiva coincide con un tick OCR,
                    # el segundo terminado pertenecía al estado anterior.
                    if delta > 0 and self.previous_states.get(name) is False:
                        self.running[name] = self.running.get(name, 0) + delta
                        self.total_seconds += delta
                        delta_for_name = 0
                    else:
                        delta_for_name = delta
                    start = valid_time if valid_time is not None else 0
                    self.probes[name] = [start, 0, 1]
                else:
                    probe[2] += 1
                    delta_for_name = delta
                probe = self.probes[name]
                if delta_for_name > 0:
                    probe[1] += delta_for_name
                if (valid_time is not None and self.valid_clock and
                        valid_time - probe[0] >= self.confirm_seconds and
                        probe[2] >= 2):
                    # Producción real: no sumar el tiempo reservado y reiniciar
                    # IDLE actual, sin decrementar el acumulado ya publicado.
                    self.confirmed[name] = True
                    self.running[name] = 0
                    self.probes.pop(name, None)
            elif was is False and value is False:
                probe = self.probes.pop(name, None)
                if probe is not None:
                    # Parpadeo: añadir todos los segundos que estaban en duda.
                    self.running[name] = self.running.get(name, 0) + probe[1]
                    self.total_seconds += probe[1]
                if delta > 0 and self.previous_states.get(name) is False:
                    self.running[name] = self.running.get(name, 0) + delta
                    self.total_seconds += delta
            elif was is True and value is True:
                self.probes.pop(name, None)
            # None sigue siendo incierto, nunca equivale a producción.
        self.previous_states = dict(self.confirmed)
        snap = self.snapshot(self.confirmed)
        snap['pendientes_produccion'] = sorted(self.probes)
        return snap


def pause_image_is_active(frame, rect, paused_reference, normal_reference):
    """Compara la región calibrada tanto con pausa como con partida reanudada."""
    if not rect or paused_reference is None or normal_reference is None:
        return False
    x,y,w,h = rect
    if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
        return False
    region = cv2.cvtColor(frame[y:y+h,x:x+w], cv2.COLOR_BGR2GRAY)
    if region.shape != paused_reference.shape or region.shape != normal_reference.shape:
        return False
    # Comparación relativa: un color estático del escenario no debe valer como pausa.
    d_paused = float(np.mean(cv2.absdiff(region, paused_reference)))
    d_normal = float(np.mean(cv2.absdiff(region, normal_reference)))
    baseline = float(np.mean(cv2.absdiff(paused_reference, normal_reference)))
    return baseline >= 8.0 and d_paused < baseline * 0.48 and d_paused < d_normal * 0.64


def capture_after_pause_button(monitor, seconds=5):
    """Captura después de que el usuario pulse su tecla de pausa configurada.

    No sintetiza pulsaciones ni requiere F3. El usuario controla el juego.
    """
    time.sleep(seconds)
    with mss.mss() as sct:
        return grab_monitor(sct, monitor)


class MatchClockResetDetector:
    """Detecta nueva partida aunque la primera lectura sea 00:00:30.

    Si el reloj ya observado supera 35 s y después baja >=30 s a un valor
    de los 120 primeros segundos, se exigen DOS lecturas coherentes y
    progresivas de ese reloj bajo. No se reinicia por una sola lectura OCR.
    """
    EARLY_WINDOW = 120
    PREVIOUS_MINIMUM = 35
    MIN_DROP = 30

    def __init__(self):
        self.last_good = None
        self.candidate = None
        self.candidate_count = 0
        self.reference_high = None

    def observe(self, seconds):
        if seconds is None:
            self.candidate = None
            self.candidate_count = 0
            self.reference_high = None
            return False
        seconds = int(seconds)
        if seconds < 0:
            return False
        if self.last_good is None:
            self.last_good = seconds
            return False

        if self.candidate is not None:
            # Segunda lectura: mismo reloj o avance de hasta 6 s.
            if (self.candidate - 1 <= seconds <= self.candidate + 6
                    and seconds <= self.EARLY_WINDOW):
                self.candidate_count += 1
                self.candidate = seconds
                if self.candidate_count >= 2:
                    self.last_good = seconds
                    self.candidate = None
                    self.candidate_count = 0
                    self.reference_high = None
                    return True
                return False
            # OCR erróneo o reloj que volvió a su valor normal: descartar.
            self.candidate = None
            self.candidate_count = 0
            self.reference_high = None

        if (self.last_good >= self.PREVIOUS_MINIMUM
                and seconds <= self.EARLY_WINDOW
                and self.last_good - seconds >= self.MIN_DROP):
            self.candidate = seconds
            self.candidate_count = 1
            self.reference_high = self.last_good
            return False

        # No introducir lecturas hacia atrás ni saltos enormes hacia delante.
        if self.last_good <= seconds <= self.last_good + 20:
            self.last_good = seconds
        return False


class ScrollableTab(ttk.Frame):
    """Panel desplazable con barra vertical visible, sin recortar ajustes."""
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0,
                                takefocus=0, bg=PARCHMENT)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical',
                                      command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = parchment_panel(self.canvas, padx=10, pady=12)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.content, anchor='nw')
        self.content.bind('<Configure>', self._refresh_scrollregion)
        self.canvas.bind('<Configure>', self._fit_width)

    def _refresh_scrollregion(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _fit_width(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        self._refresh_scrollregion()

    def wheel(self, event):
        if getattr(event, 'num', None) == 4:
            steps = -3
        elif getattr(event, 'num', None) == 5:
            steps = 3
        else:
            delta = getattr(event, 'delta', 0)
            if not delta:
                return
            steps = -3 if delta > 0 else 3
        self.canvas.yview_scroll(steps, 'units')


class VisualAlert:
    """Overlay Tk de aviso, operado exclusivamente desde el hilo principal."""
    def __init__(self, root, log):
        self.root = root
        self.log = log
        self.window = None
        self._settings_key = None
        self._appearance_key = None
        self._visible = False
        self.time_label = None
        self.loss_label = None
        self._test_until = 0.0
        self._heartbeat_running = False

    def _native_hwnd(self):
        """Tk puede devolver el HWND de un hijo: obtener SIEMPRE la ventana exterior.

        Es imprescindible para mover un Toplevel a un monitor diferente en Windows.
        """
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetAncestor.restype = ctypes.c_void_p
        raw = int(self.window.winfo_id())
        ancestor = user32.GetAncestor(ctypes.c_void_p(raw), 2)  # GA_ROOT
        if not ancestor:
            raise RuntimeError('No se ha podido obtener la ventana nativa del aviso.')
        return ctypes.c_void_p(ancestor)

    def _place_native(self):
        """Mover el HWND real, comprobar ubicación y conservar z-order sin activar."""
        if os.name != 'nt' or self.window is None:
            return
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_uint]
        user32.SetWindowPos.restype = ctypes.c_int
        hwnd = self._native_hwnd()
        x, y, w, h = self._target_rect
        # HWND_TOPMOST=-1, SWP_NOACTIVATE=0x10, SWP_SHOWWINDOW=0x40
        ok = user32.SetWindowPos(hwnd, ctypes.c_void_p(-1), x, y, w, h, 0x10|0x40)
        if not ok:
            raise ctypes.WinError()
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
        user32.GetWindowRect.restype = ctypes.c_int
        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if abs(rect.left-x)>12 or abs(rect.top-y)>12:
                # Fallo visible para facilitar diagnóstico, no afirmar éxito.
                if getattr(self, '_last_bad_pos', None) != (rect.left, rect.top, x, y):
                    self._last_bad_pos = (rect.left, rect.top, x, y)
                    self.log(f'AVISO MAL POSICIONADO: real=({rect.left},{rect.top}), destino=({x},{y}). Comprueba escalado y DPI.')

    def _resolve_image(self, settings):
        custom = settings.get('imagen_visual', '').strip()
        candidate = Path(custom) if custom else BASE / 'aviso_visual.png'
        try:
            return Image.open(candidate).convert('RGBA')
        except Exception as exc:
            if custom:
                self.log('No se pudo cargar imagen personalizada; se usara la predeterminada: '+str(exc))
            return Image.open(BASE / 'aviso_visual.png').convert('RGBA')

    def _build(self, settings):
        background, text_color = hud_colors(settings)
        self.text_color = text_color
        self.hide()
        if self.window is not None:
            self.window.destroy()
            self.window = None
        scale = max(50, min(180, int(settings.get('visual_escala', 100))))
        size = max(80, min(480, int(settings.get('visual_tamano', 260))))
        if settings.get('visual_alerta_grande', True):
            size = max(240, size)
        size = max(50, round(size * scale / 100))
        image = self._resolve_image(settings)
        corner = settings.get('visual_esquina', 'inferior_derecha')
        if settings.get('visual_posicion_libre', False):
            left_alert = float(settings.get('visual_pos_x', 80)) < 50
        else:
            left_alert = corner.endswith('izquierda')
        if left_alert:
            if not settings.get('imagen_visual', '').strip():
                with Image.open(BASE / 'aldeano_azul.png') as portrait:
                    image = portrait.convert('RGBA')
            # Usar toda la anchura útil y ceder espacio vertical a la imagen.
            # Recortar solo el margen transparente, sin deformar el dibujo.
            bounds = image.getbbox()
            if bounds:
                image = image.crop(bounds)
            image_width = round(size * 0.88 * math.sqrt(2))
            ratio = min(image_width / image.width, size * math.sqrt(2) / image.height)
            image = image.resize((max(1, round(image.width * ratio)),
                                  max(1, round(image.height * ratio))), Image.Resampling.LANCZOS)
            art = image
        else:
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            art = Image.new('RGBA', (size, size))
            art.alpha_composite(image, ((size-image.width)//2,(size-image.height)//2))
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.configure(bg=background)
        opacity = max(30, min(100, int(settings.get('visual_opacidad', 95))))/100
        if os.name != 'nt':
            win.wm_attributes('-alpha', opacity)
        outer = parchment_panel(win, vine_row=0, appearance=settings, bd=0, highlightthickness=max(2, round(PANEL_BORDER * scale / 100)),
                         highlightbackground=GOLD_BORDER, highlightcolor=GOLD_BORDER)
        outer.pack(fill='both', expand=True)
        outer = outer.content
        if settings.get('imagen_visual') == str(BASE / GOAL_PORTRAIT):
            banner = dict(bg=background, wraplength=max(140, art.width),
                          padx=round(10 * scale / 100), pady=round(8 * scale / 100))
            if settings.get('objetivo_cumplido', True):
                PulsingHudLabel(outer, text=settings.get('texto_objetivo', GOAL_BANNERS[0]),
                                size=scaled_font(15, scale), color=text_color, **banner).pack(fill='x')
            else:
                HudLabel(outer, text=MISSED_GOAL_BANNER, fg=MISSED_GOAL_COLOR,
                         font=('Segoe UI', scaled_font(15, scale), 'bold'), **banner).pack(fill='x')
        else:
            PulsingHudLabel(outer, text='CREA ALDEANOS !!', size=scaled_font(13, scale),
                            color=text_color, bg=background, padx=round(15 * scale / 100),
                            pady=round(8 * scale / 100)).pack(fill='x')
        HudLabel(outer, art=art, bg=background, borderwidth=0,
                 highlightthickness=0).pack(padx=round((2 if left_alert else 8)*scale/100),
                                           pady=(round(4*scale/100), 0))
        show_metrics = settings.get('mostrar_perdidas', True)
        if show_metrics:
            panel = hud_group(outer, bg=background, padx=round((4 if left_alert else 12)*scale/100),
                             pady=round((2 if left_alert else 6)*scale/100))
            panel.pack(fill='x', expand=True)
            if left_alert:
                panel.columnconfigure((0, 1), weight=1, uniform='metrics')
            time_caption = HudLabel(panel, text='TIEMPO IDLE', fg=text_color, bg=background,
                     font=('Segoe UI', scaled_font(12,scale), 'bold'))
            self.time_label = HudLabel(panel, text='--:--', fg=text_color, bg=background,
                                        font=('Consolas', max(scaled_font(21,scale), size // 8), 'bold'))

            loss_caption = HudLabel(panel, text='SIN CREAR' if left_alert else 'ALDEANOS NO CREADOS', fg=text_color, bg=background,
                     font=('Segoe UI', scaled_font(12,scale), 'bold'))
            self.loss_label = HudLabel(panel, text='--', fg=text_color, bg=background,
                                      font=('Consolas', max(scaled_font(21,scale), size // 8) if left_alert
                                            else max(scaled_font(28,scale), size // 6), 'bold'))
            if left_alert:
                time_caption.grid(row=0, column=0)
                loss_caption.grid(row=0, column=1)
                self.time_label.grid(row=1, column=0)
                self.loss_label.grid(row=1, column=1)
            else:
                time_caption.pack()
                self.time_label.pack()
                tk.Frame(panel, height=4, bg=GOLD_BORDER).pack(fill='x', pady=(3, 8))
                loss_caption.pack()
                self.loss_label.pack()
                HudLabel(panel, text='Estimación: 1 aldeano cada 25 s por TC vigilado',
                         fg=text_color, bg=background, font=('Segoe UI', scaled_font(8,scale))).pack(pady=(4, 0))
        else:
            self.time_label = None
            self.loss_label = None
        win.update_idletasks()
        # Coordenadas absolutas del escritorio virtual: los monitores a la
        # izquierda/encima del principal pueden tener X/Y negativas.
        with mss.mss() as sct:
            mons = sct.monitors
            selected = int(settings.get('visual_monitor', 1))
            if not 1 <= selected < len(mons):
                selected = 1
                self.log('El monitor de aviso ya no está conectado; se usa el monitor 1.')
            monitor = mons[selected]
            left, top = int(monitor['left']), int(monitor['top'])
            screenw, screenh = int(monitor['width']), int(monitor['height'])
        margin = 30
        win.update_idletasks()
        full_height = win.winfo_reqheight()
        full_width = win.winfo_reqwidth()
        if settings.get('visual_posicion_libre', False):
            # 0% = extremo izquierdo/superior; 100% = derecho/inferior.
            # Limitar la posición a lo realmente disponible evita que el aviso
            # termine parcial o completamente fuera de la pantalla.
            pct_x = max(0.0, min(100.0, float(settings.get('visual_pos_x', 80)))) / 100.0
            pct_y = max(0.0, min(100.0, float(settings.get('visual_pos_y', 75)))) / 100.0
            x = left + round(max(0, screenw - full_width) * pct_x)
            y = top + round(max(0, screenh - full_height) * pct_y)
        else:
            x = left + margin if corner.endswith('izquierda') else left + max(0, screenw - full_width - margin)
            y = top + margin if corner.startswith('superior') else top + max(0, screenh - full_height - margin)
        # La sintaxis +X-Y permite los monitores situados en coordenadas negativas.
        # Tk interpreta a veces '-X' como distancia al borde derecho, por lo que
        # se fija además la posición ABSOLUTA con SetWindowPos en Windows.
        win.geometry(f'{full_width}x{full_height}+0+0')
        win.update_idletasks()
        self._target_rect = (x, y, full_width, full_height)
        self.window = win
        if os.name != 'nt':
            win.geometry(f'{full_width}x{full_height}{x:+d}{y:+d}')
        self.log(f'Aviso destinado al monitor {selected}: ({x}, {y}), {full_width}×{full_height}; área monitor ({left},{top}) {screenw}×{screenh}')
        self._settings_key = (settings.get('imagen_visual',''), size, corner, opacity, show_metrics,
                              int(settings.get('visual_monitor', 1)),
                              bool(settings.get('visual_posicion_libre', False)),
                              int(settings.get('visual_pos_x', 80)), int(settings.get('visual_pos_y', 75)), scale)

    def _raise_without_focus(self):
        if self.window is None or not self._visible:
            return
        try:
            if os.name == 'nt':
                self._place_native()
            self.window.attributes('-topmost', True)
        except Exception as exc:
            self.log('No se pudo mantener superposición: '+str(exc))

    def _heartbeat(self):
        if not self._visible:
            self._heartbeat_running = False
            return
        self._raise_without_focus()
        self.root.after(400, self._heartbeat)

    def show(self, settings):
        scale = max(50, min(180, int(settings.get('visual_escala', 100))))
        key = (settings.get('imagen_visual',''),
               max(50, round(max(240 if settings.get('visual_alerta_grande', True) else 80,
                   min(480,int(settings.get('visual_tamano',260)))) * scale / 100)),
               settings.get('visual_esquina','inferior_derecha'),
               max(30,min(100,int(settings.get('visual_opacidad',95))))/100,
               settings.get('mostrar_perdidas', True),
               int(settings.get('visual_monitor', 1)),
               bool(settings.get('visual_posicion_libre', False)),
               int(settings.get('visual_pos_x', 80)), int(settings.get('visual_pos_y', 75)), scale)
        appearance_key = tuple(settings.get(name, default) for name, default in HUD_APPEARANCE.items())
        appearance_key += (settings.get('objetivo_cumplido', True), settings.get('texto_objetivo'))
        if self.window is None or self._settings_key != key or self._appearance_key != appearance_key:
            self._build(settings)
            self._appearance_key = appearance_key
        if self._visible:
            self._raise_without_focus()
            return
        try:
            # Set a no-activate, transparent-to-mouse extended window style on Windows.
            # Prevents the overlay from becoming the foreground app (and pausing monitoring).
            if hasattr(ctypes, 'windll'):
                hwnd = self._native_hwnd()
                user32 = ctypes.windll.user32
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x20
                WS_EX_LAYERED = 0x80000
                WS_EX_NOACTIVATE = 0x08000000
                get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.GetWindowLongW
                set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.SetWindowLongW
                get_style.restype = ctypes.c_ssize_t
                get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
                set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
                self.window.deiconify()
                self.window.update_idletasks()
                current = int(get_style(hwnd, GWL_EXSTYLE))
                set_style(hwnd, GWL_EXSTYLE, current|WS_EX_TRANSPARENT|WS_EX_LAYERED|WS_EX_NOACTIVATE)
                # Windows necesita inicializar la capa antes de mostrar su contenido.
                set_alpha = user32.SetLayeredWindowAttributes
                set_alpha.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_ubyte, ctypes.c_uint]
                set_alpha.restype = ctypes.c_int
                panel = self.window.winfo_children()[0]
                color_key = sum(value << (8 * i) for i, value in enumerate(HUD_TRANSPARENT))
                flags = 0x03 if panel.hud_overhang else 0x02  # LWA_COLORKEY | LWA_ALPHA
                if not set_alpha(hwnd, color_key, round(255 * key[3]), flags):
                    # Recuperar una ventana opaca si falla la composición de la capa.
                    set_style(hwnd, GWL_EXSTYLE, (current | WS_EX_NOACTIVATE) & ~WS_EX_LAYERED)
                self._place_native()
            else:
                self.window.deiconify()
            self.window.attributes('-topmost', True)
            self._visible = True
            self.window.update_idletasks()
            self._raise_without_focus()
            if not self._heartbeat_running:
                self._heartbeat_running = True
                self.root.after(400, self._heartbeat)
        except Exception as exc:
            self.log('No se pudo mostrar el aviso visual: '+str(exc))

    def update_metrics(self, result):
        if self.time_label is None or self.loss_label is None:
            return
        if result is None:
            self.time_label.config(text='--:--')
            self.loss_label.config(text='--')
        else:
            elapsed, lost = result
            self.time_label.config(text=format_game_duration(elapsed))
            self.loss_label.config(text=str(lost))

    def hide(self):
        if self.window is not None:
            try:
                self.window.withdraw()
            except tk.TclError:
                pass
        self._visible = False

    def close(self):
        self.hide()
        if self.window is not None:
            self.window.destroy()
            self.window = None


class HourglassWidget(HudLabel):
    """Reproduce el GIF recortado sobre el fondo del contador."""
    def __init__(self, parent, size=120, background=PARCHMENT):
        self.frames = []
        self.durations = []
        with Image.open(BASE / 'reloj-de-arena.gif') as animation:
            for frame in ImageSequence.Iterator(animation):
                # Quita el mate blanco antes de reducir, para evitar bordes blancos.
                rgb = np.asarray(frame.convert('RGB').crop((14, 14, 526, 526)), dtype=np.float32)
                light = rgb.min(axis=2)
                neutral = rgb.max(axis=2) - light < 32
                opacity = np.where(neutral, np.clip((247 - light) / 48, 0, 1), 1)
                unmatted = np.clip(rgb - 255 * (1 - opacity[..., None]), 0, 255)
                unmatted /= np.maximum(opacity[..., None], 1 / 255)
                rgba = np.dstack((np.clip(unmatted, 0, 255), opacity * 255)).astype(np.uint8)
                picture = Image.fromarray(rgba).resize((size, size), Image.Resampling.LANCZOS)
                self.frames.append(picture)
                self.durations.append(max(20, frame.info.get('duration', 75)))
        super().__init__(parent, art=self.frames[0], bg=background, highlightthickness=0, bd=0)
        self.index = 0
        self._job = None
        self.bind('<Destroy>', self._stop, add='+')

    def set_running(self, active):
        if active and self._job is None:
            self._job = self.after(self.durations[self.index], self._advance)
        elif not active:
            self._stop()

    def _stop(self, _event=None):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def _advance(self):
        self.index = (self.index + 1) % len(self.frames)
        self.art = self.frames[self.index]
        self._paint()
        self._job = self.after(self.durations[self.index], self._advance)


class TotalIdleOverlay(VisualAlert):
    """Segundo overlay independiente: permanece visible aunque no haya alarma.

    Usa el mismo posicionamiento nativo de la alerta grande y sus protecciones
    para que no robe el foco al juego.
    """
    def __init__(self, root, log):
        super().__init__(root, log)
        self.total_label = None
        self.value_seconds = 0
        self.hourglass_active = False
        self.hourglass = None

    @staticmethod
    def overlay_settings(settings):
        return {
            **{name: settings.get(name, default) for name, default in HUD_APPEARANCE.items()},
            'imagen_visual': '__hud_idle_acumulado__',
            'visual_tamano': 220, 'visual_alerta_grande': False,
            'visual_escala': int(settings.get('idle_total_escala',100)),
            'visual_esquina': 'superior_izquierda',
            'visual_posicion_libre': True,
            'visual_monitor': int(settings.get('idle_total_monitor', 1)),
            'visual_pos_x': int(settings.get('idle_total_pos_x', 50)),
            'visual_pos_y': int(settings.get('idle_total_pos_y', 5)),
            'visual_opacidad': int(settings.get('idle_total_opacidad', 94)),
            'mostrar_perdidas': False,
        }

    def _build(self, settings):
        background, text_color = hud_colors(settings)
        self.text_color = text_color
        self.hide()
        if self.hourglass is not None:
            self.hourglass.set_running(False)
            self.hourglass=None
        if self.window is not None:
            self.window.destroy()
            self.window = None
        scale = max(50, min(180, int(settings.get('visual_escala',100))))
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        opacity = max(30, min(100, int(settings['visual_opacidad']))) / 100
        if os.name != 'nt':
            win.wm_attributes('-alpha', opacity)
        win.configure(bg=background)
        box = parchment_panel(win, vine_row=1, appearance=settings, padx=round(14*scale/100), pady=round(8*scale/100), highlightthickness=PANEL_BORDER,
                       highlightbackground=GOLD_BORDER, highlightcolor=GOLD_BORDER)
        box.pack(fill='both', expand=True)
        box = box.content
        middle=hud_group(box,bg=background)
        middle.pack(anchor='center')
        self.hourglass=HourglassWidget(middle,size=max(60,round(120*scale/100)), background=background)
        self.hourglass.pack(side='left',padx=(0,5))
        time_group = hud_group(middle, bg=background)
        time_group.pack(side='left')
        HudLabel(time_group, text='IDLE TC ACUMULADO', bg=background, fg=text_color,
                 font=('Segoe UI', scaled_font(11,scale), 'bold')).pack()
        self.total_label = HudLabel(time_group, text=format_game_duration(self.value_seconds),
                 bg=background, fg=text_color, font=('Consolas', scaled_font(28,scale), 'bold'))
        self.total_label.pack()
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        with mss.mss() as sct:
            mons = sct.monitors
            selected = settings['visual_monitor']
            if not 1 <= selected < len(mons):
                selected = 1
                self.log('Monitor del acumulado desconectado: se usa el monitor 1.')
            mon = mons[selected]
        pct_x = max(0, min(100, settings['visual_pos_x'])) / 100
        pct_y = max(0, min(100, settings['visual_pos_y'])) / 100
        x = int(mon['left']) + round(max(0, int(mon['width']) - w) * pct_x)
        y = int(mon['top']) + round(max(0, int(mon['height']) - h) * pct_y)
        win.geometry(f'{w}x{h}+0+0')
        win.update_idletasks()
        self.window = win
        self._target_rect = (x, y, w, h)
        if os.name != 'nt':
            win.geometry(f'{w}x{h}{x:+d}{y:+d}')
        self._settings_key = (settings['imagen_visual'], max(50,round(220*scale/100)), settings['visual_esquina'], opacity,
               False, settings['visual_monitor'], True, settings['visual_pos_x'], settings['visual_pos_y'], scale)
        self.log(f'IDLE acumulado monitor {selected}: x={x}, y={y}, {w}x{h}')

    def show_total(self, settings):
        super().show(self.overlay_settings(settings))
        self.update_total(self.value_seconds, self.hourglass_active)

    def update_total(self, seconds, active=False):
        self.value_seconds = max(0, int(seconds or 0))
        self.hourglass_active = bool(active)
        if self.total_label is not None:
            self.total_label.config(text=format_game_duration(self.value_seconds))
        if self.hourglass is not None and self.hourglass.winfo_exists():
            self.hourglass.set_running(self.hourglass_active and self._visible)

    def hide(self):
        super().hide()
        if self.hourglass is not None and self.hourglass.winfo_exists():
            self.hourglass.set_running(False)


class AgeIdleOverlay(VisualAlert):
    """Display independiente: tiempos, aldeanos estimados y totales por edad."""
    def __init__(self, root, log):
        super().__init__(root, log)
        self.age_value_labels = {}
        self.age_loss_labels = {}
        self.total_time_label = None
        self.total_loss_label = None
        self.unassigned_label = None
        self.current_age_label = None
        self.current_snapshot = {'age':None, 'seen':[],
            'values':{a:0 for a in AGE_ORDER},
            'lost_by_age':{a:0 for a in AGE_ORDER},
            'unassigned':0,'unassigned_lost':0,'lost_total':0,'total':0}

    @staticmethod
    def overlay_settings(settings):
        return {
            **{name: settings.get(name, default) for name, default in HUD_APPEARANCE.items()},
            'imagen_visual':'__edades_idle__',
            'visual_tamano': 220, 'visual_alerta_grande': False,
            'visual_escala': int(settings.get('edades_escala',100)),
            'visual_esquina': 'superior_izquierda',
            'visual_posicion_libre': True,
            'visual_monitor': int(settings.get('edades_monitor',1)),
            'visual_pos_x': int(settings.get('edades_pos_x',4)),
            'visual_pos_y': int(settings.get('edades_pos_y',35)),
            'visual_opacidad': int(settings.get('edades_opacidad',94)),
            'mostrar_perdidas':False,
        }

    def _build(self, settings):
        background, text_color = hud_colors(settings)
        self.text_color = text_color
        self.hide()
        if self.window is not None:
            self.window.destroy()
            self.window = None
        scale = max(50, min(180, int(settings.get('visual_escala',100))))
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost',True)
        opacity = max(30,min(100,int(settings['visual_opacidad'])))/100
        if os.name != 'nt':
            win.wm_attributes('-alpha', opacity)
        win.configure(bg=background)
        panel = parchment_panel(win,vine_row=2, appearance=settings,padx=round(14*scale/100),pady=round(10*scale/100),
                         highlightthickness=PANEL_BORDER,highlightbackground=GOLD_BORDER, highlightcolor=GOLD_BORDER)
        panel.pack(fill='both',expand=True)
        panel = panel.content
        HudLabel(panel,text='IDLE TC POR EDADES',bg=background,fg=text_color,
                 font=('Segoe UI',scaled_font(12,scale),'bold')).grid(row=0,column=0,columnspan=3,pady=(0,7))
        for col,label in [(0,'EDAD'),(1,'IDLE TC'),(2,'NO CREADOS')]:
            HudLabel(panel,text=label,bg=background,fg=text_color,
                     font=('Segoe UI',scaled_font(9,scale),'bold')).grid(row=1,column=col,sticky='w' if col==0 else 'e',padx=(0,12) if col<2 else (4,0))
        self.age_value_labels = {}
        self.age_loss_labels = {}
        for row, age in enumerate(AGE_ORDER,2):
            HudLabel(panel,text=AGE_NAMES[age],bg=background,fg=text_color,
                     font=('Segoe UI',scaled_font(10,scale)),anchor='w').grid(row=row,column=0,sticky='w',padx=(0,15),pady=3)
            val=HudLabel(panel,text='--:--',bg=background,fg=text_color,
                         font=('Consolas',scaled_font(13,scale),'bold'),anchor='e')
            val.grid(row=row,column=1,sticky='e',padx=(0,12),pady=3)
            lost=HudLabel(panel,text='--',bg=background,fg=text_color,
                          font=('Consolas',scaled_font(14,scale),'bold'),anchor='e')
            lost.grid(row=row,column=2,sticky='e',pady=3)
            self.age_value_labels[age]=val
            self.age_loss_labels[age]=lost
        tk.Frame(panel,bg=GOLD_BORDER,height=2).grid(row=6,column=0,columnspan=3,sticky='ew',pady=(9,7))
        HudLabel(panel,text='TOTAL PARTIDA',bg=background,fg=text_color,
                 font=('Segoe UI',scaled_font(10,scale),'bold')).grid(row=7,column=0,sticky='w')
        self.total_time_label=HudLabel(panel,text='00:00',bg=background,fg=text_color,
                         font=('Consolas',scaled_font(14,scale),'bold'))
        self.total_time_label.grid(row=7,column=1,sticky='e',padx=(0,12))
        self.total_loss_label=HudLabel(panel,text='0',bg=background,fg=text_color,
                         font=('Consolas',scaled_font(15,scale),'bold'))
        self.total_loss_label.grid(row=7,column=2,sticky='e')
        self.unassigned_label=HudLabel(panel,text='',bg=background,fg=text_color,
                                       font=('Segoe UI',scaled_font(8,scale)),anchor='w')
        self.unassigned_label.grid(row=8,column=0,columnspan=3,sticky='w',pady=(4,0))
        self.current_age_label=HudLabel(panel,text='Edad detectada: --',bg=background,fg=text_color,
                     font=('Segoe UI',scaled_font(9,scale)),anchor='w')
        self.current_age_label.grid(row=9,column=0,columnspan=3,sticky='w',pady=(6,0))
        win.update_idletasks()
        w,h=win.winfo_reqwidth(),win.winfo_reqheight()
        with mss.mss() as sct:
            mons=sct.monitors
            idx=settings['visual_monitor']
            if not 1 <= idx < len(mons):
                idx=1
                self.log('Monitor de edades no conectado; se usa monitor 1.')
            mon=mons[idx]
        px=max(0,min(100,settings['visual_pos_x']))/100
        py=max(0,min(100,settings['visual_pos_y']))/100
        x=int(mon['left'])+round(max(0,int(mon['width'])-w)*px)
        y=int(mon['top'])+round(max(0,int(mon['height'])-h)*py)
        win.geometry(f'{w}x{h}+0+0')
        win.update_idletasks()
        self.window=win
        self._target_rect=(x,y,w,h)
        if os.name!='nt':
            win.geometry(f'{w}x{h}{x:+d}{y:+d}')
        self._settings_key=(settings['imagen_visual'],max(50,round(220*scale/100)),settings['visual_esquina'],opacity,
                            False,settings['visual_monitor'],True,settings['visual_pos_x'],settings['visual_pos_y'],scale)
        self.log(f'IDLE por edades: monitor {idx}, x={x}, y={y}, {w}x{h}')
        self.update_ages(self.current_snapshot)

    def show_ages(self, settings):
        super().show(self.overlay_settings(settings))
        self.update_ages(self.current_snapshot)

    def update_ages(self, snapshot):
        if snapshot is None:
            return
        self.current_snapshot=snapshot
        for age,label in self.age_value_labels.items():
            seen=age in snapshot.get('seen',[])
            value=snapshot.get('values',{}).get(age,0)
            lost=snapshot.get('lost_by_age',{}).get(age, value//25)
            label.config(text=format_game_duration(value) if seen else '--:--',
                         fg=self.text_color)
            self.age_loss_labels[age].config(text=str(lost) if seen else '--',
                         fg=self.text_color)
        if self.total_time_label is not None:
            self.total_time_label.config(text=format_game_duration(snapshot.get('total',0)))
        if self.total_loss_label is not None:
            self.total_loss_label.config(text=str(snapshot.get('lost_total',0)))
        if self.unassigned_label is not None:
            seconds=snapshot.get('unassigned',0)
            lost=snapshot.get('unassigned_lost',0)
            self.unassigned_label.config(text=('Sin edad asignada: '+format_game_duration(seconds)+
                ' / '+str(lost)+' aldeanos' if seconds or lost else ''))
        if self.current_age_label is not None:
            self.current_age_label.config(text='Edad detectada: '+AGE_NAMES.get(snapshot.get('age'),'sin identificar'))


class GameControlDock(VisualAlert):
    """Mandos interactivos para sonido, pausa y visibilidad de los tres HUD."""
    def __init__(self, root, log, mute_callback, pause_callback, visibility_callback):
        super().__init__(root, log)
        self.mute_callback=mute_callback
        self.pause_callback=pause_callback
        self.visibility_callback=visibility_callback
        self.visibility_buttons={}
        self.visibility_state={'total': False, 'visual': True, 'ages': False}
        self.mute_button=None
        self.pause_button=None
        self.silenced=False
        self.manual_paused=False

    @staticmethod
    def overlay_settings(settings):
        return {**{name: settings.get(name, default) for name, default in HUD_APPEARANCE.items()},
            'imagen_visual':'__controles_aoe__','visual_tamano':220,
            'visual_escala':int(settings.get('controles_escala',100)),
            'visual_alerta_grande':False,'visual_esquina':'superior_izquierda',
            'visual_posicion_libre':True,
            'visual_monitor':int(settings.get('controles_monitor',1)),
            'visual_pos_x':int(settings.get('controles_pos_x',70)),
            'visual_pos_y':int(settings.get('controles_pos_y',3)),
            'visual_opacidad':int(settings.get('controles_opacidad',96)),
            'mostrar_perdidas':False}

    def _build(self, settings):
        background, text_color = hud_colors(settings)
        self.text_color = text_color
        self.button_background = background
        self.hide()
        if self.window is not None:
            self.window.destroy()
        scale=max(50,min(180,int(settings.get('visual_escala',100))))
        win=tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost',True)
        opacity=max(30,min(100,int(settings['visual_opacidad'])))/100
        if os.name != 'nt':
            win.wm_attributes('-alpha', opacity)
        win.configure(bg=background)
        panel=parchment_panel(win,vine_row=3, appearance=settings,padx=round(5*scale/100),pady=round(5*scale/100),
                       highlightbackground=GOLD_BORDER, highlightcolor=GOLD_BORDER, highlightthickness=PANEL_BORDER)
        panel.pack(fill='both',expand=True)
        panel = panel.content
        self.visibility_buttons = {}
        for key, arrow in (('visual', '←'), ('total', '↑'), ('ages', '→')):
            button = tk.Button(panel, text=arrow,
                               command=lambda item=key: self.visibility_callback(item),
                               bg=background, fg=text_color, activeforeground=text_color,
                               font=('Segoe UI', scaled_font(12, scale), 'bold'),
                               activebackground=background, width=3)
            button.pack(side='left', padx=2, fill='y')
            self.visibility_buttons[key] = button
            self.paint_direction_arrow(button, scale, text_color, key)
        self.speaker_icons = tuple(self.speaker_icon(scale, text_color, muted)
                                   for muted in (False, True))
        self.mute_button = tk.Button(panel, image=self.speaker_icons[0],
                                     command=self.mute_callback, bg=background,
                                     activebackground=background, padx=5)
        self.mute_button.pack(side='left', padx=(6, 2), fill='y')
        self.pause_button = tk.Button(panel, text='Ⅱ', command=self.pause_callback,
                                      bg=background, fg=text_color, activeforeground=text_color,
                                      font=('Segoe UI', scaled_font(12, scale), 'bold'),
                                      activebackground=background, width=3)
        self.pause_button.pack(side='left', padx=2, fill='y')
        win.update_idletasks()
        w,h=win.winfo_reqwidth(),win.winfo_reqheight()
        with mss.mss() as sct:
            mons=sct.monitors
            monitor=int(settings['visual_monitor'])
            if not 1<=monitor<len(mons):
                monitor=1
            mon=mons[monitor]
        x=int(mon['left'])+round(max(0,int(mon['width'])-w)*max(0,min(100,int(settings['visual_pos_x'])))/100)
        y=int(mon['top'])+round(max(0,int(mon['height'])-h)*max(0,min(100,int(settings['visual_pos_y'])))/100)
        win.geometry(f'{w}x{h}+0+0')
        win.update_idletasks()
        self.window=win
        self._target_rect=(x,y,w,h)
        if os.name!='nt':
            win.geometry(f'{w}x{h}{x:+d}{y:+d}')
        self._settings_key=(settings['imagen_visual'],max(50,round(220*scale/100)),settings['visual_esquina'],opacity,
                            False,settings['visual_monitor'],True,settings['visual_pos_x'],settings['visual_pos_y'],scale)
        self.update_buttons(self.silenced,self.manual_paused)
        self.update_visibility(self.visibility_state)

    def show_controls(self, settings):
        super().show(self.overlay_settings(settings))
        self.update_buttons(self.silenced,self.manual_paused)
        self.update_visibility(self.visibility_state)
        self._enable_clicks()

    def _enable_clicks(self):
        """El HUD normal es click-through, pero estos botones DEBEN aceptar clics."""
        if os.name != 'nt' or self.window is None:
            return
        try:
            hwnd=self._native_hwnd()
            user32=ctypes.windll.user32
            fn_get=user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.GetWindowLongW
            fn_set=user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.SetWindowLongW
            fn_get.argtypes=[ctypes.c_void_p,ctypes.c_int]
            fn_get.restype=ctypes.c_ssize_t
            fn_set.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_ssize_t]
            style=int(fn_get(hwnd,-20))
            fn_set(hwnd,-20,style & ~0x20) # quitar WS_EX_TRANSPARENT
        except Exception as exc:
            self.log('No se pudo activar botones flotantes: '+str(exc))

    def speaker_icon(self, scale, color, muted):
        size = max(18, round(29 * scale / 100))
        icon = Image.new('RGBA', (96, 96))
        draw = ImageDraw.Draw(icon)
        draw.polygon(((9, 36), (25, 36), (48, 16), (48, 80), (25, 60), (9, 60)), fill=color)
        if muted:
            draw.line(((60, 36), (84, 60)), fill=color, width=6)
            draw.line(((60, 60), (84, 36)), fill=color, width=6)
        else:
            draw.arc((38, 27, 77, 69), -55, 55, fill=color, width=5)
            draw.arc((38, 13, 92, 83), -55, 55, fill=color, width=5)
        return ImageTk.PhotoImage(icon.resize((size, size), Image.Resampling.LANCZOS),
                                 master=self.root)

    def paint_direction_arrow(self, button, scale, color, direction):
        width = max(26, round(41 * scale / 100))
        height = max(24, round(31 * scale / 100))
        button.face = tk.PhotoImage(master=button, width=width, height=height)
        button.config(image=button.face, width=width, height=height, padx=0, pady=0)

        def render(paper):
            x, y = (paper.width - width) // 2, (paper.height - height) // 2
            face = paper.crop((x, y, x + width, y + height))
            draw = ImageDraw.Draw(face)
            cx, cy = width // 2, 2 * height // 3
            length = max(7, height // 3)
            stroke = max(2, width // 16)
            dx, dy = {'visual': (-1, 0), 'total': (0, -1), 'ages': (1, 0)}[direction]

            def point(along, across=0):
                return cx + along * dx - across * dy, cy + along * dy + across * dx

            draw.line((point(-length), point(length)), fill=color, width=stroke)
            draw.line((point(length // 3, -length // 2), point(length),
                       point(length // 3, length // 2)), fill=color, width=stroke)
            button.face = ImageTk.PhotoImage(face, master=button)
            button.config(image=button.face)

        paint_on_hud(button, render)

    def update_buttons(self,silenced,manual_paused):
        self.silenced=bool(silenced)
        self.manual_paused=bool(manual_paused)
        if self.mute_button is not None:
            self.mute_button.config(image=self.speaker_icons[self.silenced],
                                    bg=self.button_background,
                                    relief='sunken' if silenced else 'raised')
        if self.pause_button is not None:
            self.pause_button.config(text='▶' if manual_paused else 'Ⅱ',
                                     bg=self.button_background,
                                     relief='sunken' if manual_paused else 'raised')


    def update_visibility(self, states):
        """Se puede ocultar o recuperar cada HUD sin detener el cronómetro."""
        self.visibility_state.update({key: bool(value) for key, value in states.items()})
        labels={'total':'↑', 'visual':'←', 'ages':'→'}
        for key, button in self.visibility_buttons.items():
            showing=self.visibility_state[key]
            button.config(text=labels[key], bg=self.button_background,
                          relief='raised' if showing else 'sunken')


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('AoE2 DE · Avisador de aldeanos v26 · IDLE por edades')
        self.root.geometry('750x610')
        self.root.minsize(680, 540)
        self.config = DEFAULTS.copy()
        # Al actualizar, importa las zonas y preferencias de la versión anterior.
        old_path = next((q for q in [CFG_FILE, *LEGACY_CONFIGS] if q.is_file()), None)
        if old_path:
            try:
                saved = json.loads(old_path.read_text(encoding='utf-8'))
                self.config.update(saved)
                self._validate_zone_data(self.config)
                if old_path != CFG_FILE:
                    self.save()
            except Exception as exc:
                messagebox.showwarning('Configuración', f'No se pudo restaurar: {exc}')
        saved_revision=(saved.get('version_detector_edad',0) if
                        old_path and 'saved' in locals() and isinstance(saved,dict) else 22)
        if saved_revision < 22:
            # El rótulo textual calibrado en V21 NO representa el escudo.
            # Conservar la antigua zona como copia, sin atribuir edades erróneas.
            if self.config.get('zona_edad'):
                self.config['zona_edad_texto_v21'] = self.config['zona_edad']
            self.config['zona_edad'] = None
            self.config['version_detector_edad'] = 26
            self.save()
        self.msg_queue = queue.Queue(maxsize=2000)
        self.stop_event = threading.Event()
        self.thread = None
        self.sound_engine = SoundEngine(self.log)
        self.visual_alert = VisualAlert(self.root, self.log)
        self.total_idle_overlay = TotalIdleOverlay(self.root, self.log)
        self.age_idle_overlay = AgeIdleOverlay(self.root, self.log)
        self.manual_pause_event = threading.Event()
        self.muted_event = threading.Event()
        self.game_controls = GameControlDock(self.root, self.log,
                                              self.toggle_mute, self.toggle_manual_pause,
                                              self.toggle_overlay_visibility)
        self.preview_controls_active=False
        self.reset_total_event = threading.Event()
        self.red_on_var=tk.BooleanVar(value=self.config.get('rojo_activo',True))
        self.technology_on_var=tk.BooleanVar(value=self.config.get('tecnologias_activo',True))
        self.visual_enabled_var=tk.BooleanVar(value=self.config.get('mostrar_aviso_visual',True))
        self.hold_var = tk.StringVar(value=str(self.config.get('visual_permanencia', 2)))
        self.ocr_interval_var = tk.StringVar(value=str(self.config.get('ocr_intervalo', .38)))
        self.flicker_filter_var = tk.StringVar(value=str(self.config.get('filtro_parpadeo_segundos', 1)))
        self.latest_metrics = None
        self.running_settings = None
        self.celebration_job = None
        self.goal_achieved = True
        self.goal_banner = GOAL_BANNERS[0]
        self.latest_visual_snapshot = None
        self.imperial_checked = False
        self.mode_var = tk.StringVar(value=self.config['modo'])
        self.monitor_var = tk.StringVar(value=str(self.config['monitor']))
        self.threshold_var = tk.StringVar(value=str(self.config['umbral']))
        self.wait_var = tk.StringVar(value='3')
        self.sound_var = tk.StringVar(value=self.config['sonido'])
        self.custom_file_var = tk.StringVar(value=self.config['archivo_sonido'])
        self.volume_var = tk.IntVar(value=self.config['volumen'])
        self.channel_var = tk.StringVar(value=self.config['canal_aviso'])
        self.visual_file_var = tk.StringVar(value=self.config['imagen_visual'])
        self.visual_size_var = tk.IntVar(value=self.config['visual_tamano'])
        self.visual_scale_var = tk.IntVar(value=self.config.get('visual_escala',100))
        self.visual_big_var = tk.BooleanVar(value=self.config.get('visual_alerta_grande', True))
        self.visual_corner_var = tk.StringVar(value=self.config['visual_esquina'])
        self.visual_free_var = tk.BooleanVar(value=self.config.get('visual_posicion_libre', False))
        self.visual_x_var = tk.IntVar(value=self.config.get('visual_pos_x', 80))
        self.visual_y_var = tk.IntVar(value=self.config.get('visual_pos_y', 75))
        self.hud_appearance_vars = {
            name: tk.StringVar(value=self.config.get(name, default))
            for name, default in HUD_APPEARANCE.items()
        }
        self.visual_opacity_var = tk.IntVar(value=self.config['visual_opacidad'])
        self.visual_monitor_var = tk.StringVar()
        self.visual_monitor_map = {}
        self.losses_var = tk.BooleanVar(value=self.config.get('mostrar_perdidas', True))
        self.auto_restart_var = tk.BooleanVar(value=self.config.get('reiniciar_al_reloj_cero', True))
        self.idle_total_on_var = tk.BooleanVar(value=self.config.get('idle_total_visible', False))
        self.idle_total_x_var = tk.IntVar(value=self.config.get('idle_total_pos_x', 50))
        self.idle_total_y_var = tk.IntVar(value=self.config.get('idle_total_pos_y', 5))
        self.idle_total_alpha_var = tk.IntVar(value=self.config.get('idle_total_opacidad', 94))
        self.idle_total_scale_var = tk.IntVar(value=self.config.get('idle_total_escala',100))
        self.idle_total_monitor_var = tk.StringVar()
        self.idle_total_monitor_map = {}
        self.idle_total_text_var = tk.StringVar(value='00:00')
        self.age_overlay_on_var = tk.BooleanVar(value=self.config.get('edades_visible', False))
        self.age_x_var = tk.IntVar(value=self.config.get('edades_pos_x', 4))
        self.age_y_var = tk.IntVar(value=self.config.get('edades_pos_y',35))
        self.age_alpha_var = tk.IntVar(value=self.config.get('edades_opacidad',94))
        self.age_scale_var = tk.IntVar(value=self.config.get('edades_escala',100))
        self.age_monitor_var = tk.StringVar()
        self.age_monitor_map = {}
        self.control_on_var = tk.BooleanVar(value=self.config.get('controles_visible', True))
        self.control_x_var = tk.IntVar(value=self.config.get('controles_pos_x',70))
        self.control_y_var = tk.IntVar(value=self.config.get('controles_pos_y',3))
        self.control_opacity_var = tk.IntVar(value=self.config.get('controles_opacidad',96))
        self.control_scale_var = tk.IntVar(value=self.config.get('controles_escala',100))
        self.control_monitor_var = tk.StringVar()
        self.control_monitor_map = {}
        self.current_age_var = tk.StringVar(value='Sin detectar · Calibra escudo y/o texto de edad')
        self.last_age_snapshot = None
        self.limit_time_on_var = tk.BooleanVar(value=self.config['limite_tiempo_activo'])
        self.limit_time_var = tk.StringVar(value=str(self.config['limite_minutos']))
        self.limit_pop_on_var = tk.BooleanVar(value=self.config['limite_aldeanos_activo'])
        self.limit_pop_var = tk.StringVar(value=str(self.config['limite_aldeanos']))
        self.repeat_var = tk.IntVar(value=int(round(float(self.config['repeticion']))))
        self.live_repeat_seconds = float(self.config['repeticion'])
        self.foreground_var = tk.BooleanVar(value=self.config['solo_juego_activo'])
        self.status_var = tk.StringVar(value='SIN INICIAR')
        self.details_var = tk.StringVar(value='Calibra y pulsa Iniciar.')
        self._create_widgets()
        self.root.bind_all('<MouseWheel>', self._on_mouse_wheel, add='+')
        self.root.bind_all('<Button-4>', self._on_mouse_wheel, add='+')
        self.root.bind_all('<Button-5>', self._on_mouse_wheel, add='+')
        self.root.after(120, self.process_messages)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def _create_widgets(self):
        self.root.geometry('790x720')
        pad = parchment_panel(self.root, vine_row=4, padx=12, pady=12,
                              highlightthickness=PANEL_BORDER, highlightbackground=GOLD_BORDER,
                              highlightcolor=GOLD_BORDER)
        pad.pack(fill='both', expand=True)
        pad = pad.content
        ttk.Label(pad, text='Avisador de aldeanos · Age of Empires II: DE · V21',
                  font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        ttk.Label(pad, text='Reconocimiento de pantalla · Voz, pitidos o MP3/WAV · Usa la barra a la derecha para bajar.').pack(anchor='w', pady=(3, 8))
        tabs = ttk.Notebook(pad)
        tabs.pack(fill='both', expand=True)
        self.scrollable_tabs = []
        for heading in ('Detección y límites', 'Sonido y volumen', 'Aviso visual',
                        'IDLE acumulado', 'IDLE por edades', 'Objetivos IDLE'):
            tab = ScrollableTab(tabs)
            tabs.add(tab, text=heading)
            self.scrollable_tabs.append(tab)
        self.tabs = tabs
        setup, sound_tab, visual_tab, idle_tab, age_tab, goals_tab = [
            tab.content for tab in self.scrollable_tabs]
        self.create_idle_goals(goals_tab)
        lf = ttk.LabelFrame(setup, text='1. Detección de producción', padding=8)
        lf.pack(fill='x', pady=5)
        ttk.Radiobutton(lf, text='Global: ausencia de aldeanos en la cola visible',
                        variable=self.mode_var, value='global').pack(anchor='w')
        ttk.Radiobutton(lf, text='Individual: un indicador propio y siempre visible para cada centro urbano',
                        variable=self.mode_var, value='individual').pack(anchor='w')
        ttk.Label(lf, text='Reconoce iconos, no solo el color verde. La cola global NO identifica cada TC.',
                  foreground=GOLD_TEXT).pack(anchor='w', pady=4)
        lf2 = ttk.LabelFrame(setup, text='2. Calibración', padding=8)
        lf2.pack(fill='x', pady=6)
        row = ttk.Frame(lf2)
        row.pack(fill='x')
        ttk.Label(row, text='Monitor:').pack(side='left')
        ttk.Entry(row, width=4, textvariable=self.monitor_var).pack(side='left', padx=5)
        ttk.Label(row, text='Similitud:').pack(side='left', padx=(9, 0))
        ttk.Entry(row, width=5, textvariable=self.threshold_var).pack(side='left', padx=5)
        ttk.Button(row, text='Calibrar pantalla', command=self.calibrate).pack(side='right')
        row_zones = ttk.Frame(lf2)
        row_zones.pack(fill='x', pady=(5, 0))
        ttk.Button(row_zones,text='Calibrar icono ROJO',command=self.calibrate_red).pack(side='left',padx=(0,8))
        ttk.Button(row_zones, text='Calibrar pausa (cualquier tecla)', command=self.calibrate_pause).pack(side='left', padx=(0, 9))
        ttk.Button(row_zones, text='Calibrar escudo', command=self.calibrate_age).pack(side='left', padx=(0,9))
        ttk.Button(row_zones, text='Exportar zonas…', command=self.export_zones).pack(side='left')
        ttk.Button(row_zones, text='Importar zonas…', command=self.import_zones).pack(side='left', padx=7)
        ttk.Label(row_zones, text='Zonas guardadas automáticamente.', foreground=GOLD_TEXT).pack(side='left')
        ttk.Label(lf2, text='Primer aviso tras 3 s de IDLE del reloj de partida. Repetición configurable en «Sonido y volumen».',
                  wraplength=650).pack(anchor='w', pady=(7, 0))
        ttk.Checkbutton(lf2, text='Pausar si el juego no está en primer plano', variable=self.foreground_var).pack(anchor='w', pady=3)
        ttk.Button(lf2, text='Calibrar TEXTO de edad (blanco/amarillo)', command=self.calibrate_age_text).pack(anchor='w', pady=4)
        ttk.Checkbutton(lf2,text='Contar como IDLE el icono rojo calibrado (aunque se vea aldeano)',variable=self.red_on_var).pack(anchor='w',pady=3)
        ttk.Label(lf2,text='Calibra el indicador ROJO con el icono realmente rojo. Su zona queda guardada y tendrá prioridad frente a la plantilla hombre/mujer.',foreground=GOLD_TEXT,wraplength=660).pack(anchor='w',pady=2)
        ttk.Label(lf2, text='Todos los segundos IDLE se obtienen exclusivamente del reloj OCR de la partida.', wraplength=670, foreground=GOLD_TEXT).pack(anchor='w')
        ttk.Label(lf2, text='Calibrar pausa: pulsa tu tecla o botón habitual de pausa antes de cada captura. No se necesita F3.', wraplength=670).pack(anchor='w', pady=2)
        line_ocr = ttk.Frame(lf2); line_ocr.pack(fill='x', pady=4)
        ttk.Label(line_ocr, text='Lectura OCR cada (s):').pack(side='left')
        ttk.Entry(line_ocr, width=7, textvariable=self.ocr_interval_var).pack(side='left', padx=6)
        ttk.Label(line_ocr, text='0,3–1,5; el reloj tiene resolución de 1 segundo.').pack(side='left')
        line_filter = ttk.Frame(lf2); line_filter.pack(fill='x', pady=4)
        ttk.Label(line_filter, text='Confirmar producción tras (s de juego):').pack(side='left')
        ttk.Combobox(line_filter, textvariable=self.flicker_filter_var,
                     values=('1', '2', '3'), state='readonly', width=4).pack(side='left', padx=7)
        ttk.Label(line_filter, text='Evita reinicios por parpadeos; recupera segundos dudosos.').pack(side='left')
        self.calib_label = ttk.Label(lf2, text='Sin calibrar')
        self.calib_label.pack(anchor='w')
        self.refresh_calib_label()
        ttk.Checkbutton(lf2, text='Reconocer tecnologías del centro urbano como PRODUCCIÓN activa (también con progreso verde)',
                        variable=self.technology_on_var).pack(anchor='w', pady=(5, 1))
        ttk.Label(lf2, text='Incluye 23 plantillas de tecnología y 8 de aldeanos, con las 12 imágenes originales. Icono reconocido (normal/verde) = activo; rojo o sin iconos = IDLE. Calibra solo la cola.',
                  wraplength=665, foreground=GOLD_TEXT).pack(anchor='w')
        limits = ttk.LabelFrame(setup, text='3. Detención automática de avisos (ambos límites opcionales)', padding=8)
        limits.pack(fill='x', pady=6)
        r1 = ttk.Frame(limits)
        r1.pack(fill='x', pady=3)
        ttk.Checkbutton(r1, text='Dejar de avisar a partir del minuto de partida:',
                        variable=self.limit_time_on_var).pack(side='left')
        ttk.Entry(r1, width=6, textvariable=self.limit_time_var).pack(side='left', padx=6)
        r2 = ttk.Frame(limits)
        r2.pack(fill='x', pady=3)
        ttk.Checkbutton(r2, text='Dejar de avisar al alcanzar estos aldeanos:',
                        variable=self.limit_pop_on_var).pack(side='left')
        ttk.Entry(r2, width=6, textvariable=self.limit_pop_var).pack(side='left', padx=6)
        ttk.Checkbutton(limits, text='Reiniciar al retroceder el reloj a los primeros 2 minutos (p. ej. 00:00:30)',
                        variable=self.auto_restart_var).pack(anchor='w', pady=(6, 2))
        ttk.Label(limits, text='El reloj se lee incluso después de alcanzar un límite. Detecta saltos a 00:00:30 o similares; se confirman dos lecturas; requiere zona del reloj calibrada y Tesseract OCR.',
                  wraplength=680).pack(anchor='w', pady=(1, 4))
        ttk.Label(limits, text='Hay que seleccionar el reloj y/o contador en la calibración. Requiere Tesseract OCR.',
                  foreground=GOLD_TEXT, wraplength=700).pack(anchor='w', pady=(4, 0))
        audio = ttk.LabelFrame(sound_tab, text='Tipo de aviso', padding=12)
        audio.pack(fill='x', pady=6)
        for value, label in [('voz', 'Voz de Windows: «Crea aldeanos»'),
                             ('doble', 'Dos pitidos'), ('triple', 'Tres pitidos'),
                             *((key, label) for key, (label, _) in BUILTIN_ALERTS.items()),
                             ('archivo', 'Archivo de sonido propio (MP3 o WAV)')]:
            ttk.Radiobutton(audio, text=label, variable=self.sound_var, value=value).pack(anchor='w', pady=3)
        row_file = ttk.Frame(audio)
        row_file.pack(fill='x', pady=8)
        ttk.Button(row_file, text='Elegir MP3/WAV…', command=self.select_sound).pack(side='left')
        ttk.Label(row_file, textvariable=self.custom_file_var, wraplength=460).pack(side='left', padx=9)
        volume_box = ttk.LabelFrame(sound_tab, text='Volumen del aviso', padding=12)
        volume_box.pack(fill='x', pady=6)
        volume_row = ttk.Frame(volume_box)
        volume_row.pack(fill='x')
        ttk.Scale(volume_row, from_=0, to=100, variable=self.volume_var,
                  orient='horizontal', length=450).pack(side='left', fill='x', expand=True)
        ttk.Label(volume_row, textvariable=self.volume_var, width=4).pack(side='left', padx=8)
        ttk.Label(volume_box, text='Se aplica a los MP3/WAV, pitidos y voz. No modifica el volumen general del PC.').pack(anchor='w', pady=5)
        interval_box = ttk.LabelFrame(sound_tab, text='Repetición del sonido durante IDLE TC', padding=12)
        interval_box.pack(fill='x', pady=6)
        ttk.Label(interval_box, text='Cuando el TC siga inactivo, reproducir el siguiente aviso cada:',
                  wraplength=660).pack(anchor='w', pady=(0,6))
        interval_row = ttk.Frame(interval_box); interval_row.pack(fill='x')
        tk.Scale(interval_row, variable=self.repeat_var, from_=1, to=120, resolution=1,
                 orient='horizontal', showvalue=False, length=355,
                 highlightthickness=0).pack(side='left', fill='x', expand=True)
        tk.Spinbox(interval_row, from_=1, to=120, increment=1, width=5,
                   textvariable=self.repeat_var).pack(side='left', padx=(10,5))
        ttk.Label(interval_row, text='segundos').pack(side='left')
        ttk.Label(interval_box, text='El primer aviso sigue esperando 3 s de IDLE. La repetición usa el reloj del juego; en pausa no avanza.',
                  wraplength=660, foreground=GOLD_TEXT).pack(anchor='w', pady=(6,0))
        ttk.Button(sound_tab, text='▶ Probar sonido', command=self.test_sound).pack(anchor='w', pady=8)
        ttk.Label(sound_tab, text='El sonido escogido se recuerda al abrir el programa de nuevo.').pack(anchor='w')
        ch = ttk.LabelFrame(visual_tab, text='Como quieres que te avise', padding=12)
        ch.pack(fill='x', pady=5)
        for value, title in [('ambos','Visual y sonoro a la vez'),
                             ('visual','Solo visual (silencio)'), ('sonoro','Solo sonoro')]:
            ttk.Radiobutton(ch, text=title, value=value, variable=self.channel_var).pack(anchor='w', pady=3)
        ttk.Checkbutton(visual_tab, text='Mostrar aviso visual durante las alertas (también controlable desde el juego)',
                        variable=self.visual_enabled_var, command=lambda: self.toggle_overlay_visibility('visual', from_ui=True)).pack(anchor='w', pady=4)
        pic = ttk.LabelFrame(visual_tab, text='Imagen del aviso visual', padding=12)
        pic.pack(fill='x', pady=5)
        ttk.Label(pic, text='Deja vacío el archivo para usar el icono incluido: ! + dos aldeanos.').pack(anchor='w')
        line = ttk.Frame(pic)
        line.pack(fill='x', pady=5)
        ttk.Button(line, text='Elegir imagen PNG/JPG/WebP…', command=self.choose_visual).pack(side='left')
        ttk.Button(line, text='Usar icono predeterminado', command=self.reset_visual).pack(side='left', padx=7)
        ttk.Label(pic, textvariable=self.visual_file_var, wraplength=670).pack(anchor='w')
        opts = ttk.LabelFrame(visual_tab, text='Apariencia y posición', padding=12)
        opts.pack(fill='x', pady=5)
        monitor_row = ttk.Frame(opts)
        monitor_row.pack(fill='x', pady=4)
        ttk.Label(monitor_row, text='Monitor donde mostrar el aviso:').pack(side='left')
        self.visual_monitor_box = ttk.Combobox(monitor_row, textvariable=self.visual_monitor_var,
                                              state='readonly', width=37)
        self.visual_monitor_box.pack(side='left', padx=8)
        ttk.Button(monitor_row, text='Detectar monitores', command=self.refresh_visual_monitors).pack(side='left')
        ttk.Label(opts, text='El monitor de aviso es independiente del monitor capturado.').pack(anchor='w')
        self.refresh_visual_monitors()
        sz = ttk.Frame(opts)
        sz.pack(fill='x', pady=4)
        ttk.Label(sz, text='Tamaño del icono (80–480 px):').pack(side='left')
        ttk.Scale(sz, from_=80, to=480, variable=self.visual_size_var,
                  orient='horizontal', length=270).pack(side='left', padx=8)
        ttk.Label(sz, textvariable=self.visual_size_var, width=4).pack(side='left')
        sc = ttk.Frame(opts);sc.pack(fill='x',pady=4)
        ttk.Label(sc,text='Escala de TODO el aviso (50–180 %):').pack(side='left')
        tk.Scale(sc,from_=50,to=180,resolution=5,variable=self.visual_scale_var,
                 orient='horizontal',showvalue=False,length=235,highlightthickness=0).pack(side='left')
        ttk.Label(sc,textvariable=self.visual_scale_var,width=4).pack(side='left')
        ttk.Label(sc,text='%').pack(side='left')
        ttk.Checkbutton(opts, text='Alerta grande: icono mínimo de 240 px y cifras destacadas',
                        variable=self.visual_big_var).pack(anchor='w', pady=2)
        positions = [('Inferior derecha','inferior_derecha'),('Inferior izquierda','inferior_izquierda'),
                     ('Superior derecha','superior_derecha'),('Superior izquierda','superior_izquierda')]
        ttk.Label(opts, text='Ubicación:').pack(anchor='w')
        ttk.Combobox(opts, textvariable=self.visual_corner_var, state='readonly',
                     values=[p[1] for p in positions], width=24).pack(anchor='w', pady=3)
        ttk.Checkbutton(opts, text='Posición libre (ignorar esquina y mover el icono)',
                        variable=self.visual_free_var).pack(anchor='w', pady=(4, 0))
        coord = ttk.Frame(opts)
        coord.pack(fill='x', pady=2)
        ttk.Label(coord, text='Horizontal:').grid(row=0, column=0, sticky='w', padx=(0, 5))
        ttk.Scale(coord, from_=0, to=100, variable=self.visual_x_var,
                  orient='horizontal', length=235).grid(row=0, column=1, sticky='ew')
        ttk.Label(coord, textvariable=self.visual_x_var, width=4).grid(row=0, column=2, padx=4)
        ttk.Label(coord, text='Vertical:').grid(row=1, column=0, sticky='w', padx=(0, 5))
        ttk.Scale(coord, from_=0, to=100, variable=self.visual_y_var,
                  orient='horizontal', length=235).grid(row=1, column=1, sticky='ew')
        ttk.Label(coord, textvariable=self.visual_y_var, width=4).grid(row=1, column=2, padx=4)
        ttk.Label(opts, text='0 = izquierda/arriba · 100 = derecha/abajo. Pulsa «Probar» para ver el resultado.',
                  wraplength=660).pack(anchor='w')
        op = ttk.Frame(opts)
        op.pack(fill='x', pady=5)
        ttk.Label(op, text='Opacidad:').pack(side='left')
        ttk.Scale(op, from_=30, to=100, variable=self.visual_opacity_var,
                  orient='horizontal', length=270).pack(side='left', padx=8)
        ttk.Label(op, textvariable=self.visual_opacity_var, width=4).pack(side='left')
        hold_frame = ttk.Frame(visual_tab); hold_frame.pack(fill='x', pady=6)
        ttk.Label(hold_frame, text='Mantener aviso después de reanudar producción (s de partida):').pack(side='left')
        ttk.Entry(hold_frame, width=6, textvariable=self.hold_var).pack(side='left', padx=8)
        ttk.Checkbutton(visual_tab, text='Mostrar IDLE y ALDEANOS NO CREADOS (estimación de 1 por cada 25 s)',
                        variable=self.losses_var).pack(anchor='w', pady=5)
        ttk.Label(visual_tab, text='Ambas cifras IDLE proceden ÚNICAMENTE del reloj de la partida, sin usar tiempo de Windows. '
                  'Si el reloj no se puede leer, verás --:-- y --.', wraplength=680).pack(anchor='w')
        appearance = ttk.LabelFrame(visual_tab, text='Aspecto de los marcos durante la partida', padding=8)
        appearance.pack(fill='x', pady=5)
        for text, value in (('Madera oscura', 'madera_oscura'),
                            ('Madera rústica', 'madera_rustica'), ('Color liso', 'color')):
            ttk.Radiobutton(appearance, text=text, value=value,
                            variable=self.hud_appearance_vars['marco_fondo']).pack(side='left', padx=4)
        ttk.Button(appearance, text='Color de fondo',
                   command=lambda: self.choose_hud_color('marco_color_fondo')).pack(side='left', padx=4)
        ttk.Button(appearance, text='Color de letras',
                   command=lambda: self.choose_hud_color('marco_color_letras')).pack(side='left', padx=4)
        frame_choices = ttk.Frame(visual_tab)
        frame_choices.pack(fill='x', pady=(0, 5))
        ttk.Label(frame_choices, text='Marco de madera').pack(side='left', padx=4)
        for text, value in (('Tallada', 'madera_tallada'), ('Dorada', 'madera_dorada')):
            ttk.Radiobutton(frame_choices, text=text, value=value,
                            variable=self.hud_appearance_vars['marco_estilo']).pack(side='left', padx=4)
        ttk.Button(visual_tab, text='PROBAR AVISO COMPLETO: ICONO + SONIDO (15 segundos)', command=self.test_visual).pack(anchor='w', pady=10)
        ttk.Label(visual_tab, text='La prueba dura 15 s: pulsa el botón y vuelve al juego inmediatamente. Usa ventana sin bordes, no pantalla completa exclusiva. El aviso real aparece solo en ALERTA.',
                  wraplength=680).pack(anchor='w')

        # Contador independiente, siempre visible, y configurable en monitor/posición.
        box_idle = ttk.LabelFrame(idle_tab, text='Contador independiente del aviso grande', padding=12)
        box_idle.pack(fill='x', pady=6)
        ttk.Checkbutton(box_idle, text='Mostrar permanentemente IDLE TC acumulado mientras monitorizo',
                        variable=self.idle_total_on_var,
                        command=lambda: self.toggle_overlay_visibility('total', from_ui=True)).pack(anchor='w', pady=(0, 8))
        ttk.Label(box_idle, text='Suma el tiempo sin producción de cada indicador vigilado. El total no se borra al volver a producir. Se reinicia al detectar una partida nueva.',
                  wraplength=650).pack(anchor='w', pady=4)
        sel = ttk.Frame(box_idle)
        sel.pack(fill='x', pady=8)
        ttk.Label(sel, text='Monitor del contador:').pack(side='left')
        self.idle_total_monitor_box = ttk.Combobox(sel, textvariable=self.idle_total_monitor_var,
                                                  width=36, state='readonly')
        self.idle_total_monitor_box.pack(side='left', padx=5)
        ttk.Button(sel, text='Actualizar', command=self.refresh_idle_monitors).pack(side='left')
        self.refresh_idle_monitors()
        resize=ttk.Frame(box_idle);resize.pack(fill='x',pady=5)
        ttk.Label(resize,text='Tamaño del display (50–180 %):').pack(side='left')
        tk.Scale(resize,from_=50,to=180,resolution=5,variable=self.idle_total_scale_var,
                 orient='horizontal',showvalue=False,length=250,highlightthickness=0).pack(side='left')
        ttk.Label(resize,textvariable=self.idle_total_scale_var,width=4).pack(side='left')
        ttk.Label(resize,text='%').pack(side='left')
        for title, var in [('Posición horizontal (0–100 %)', self.idle_total_x_var),
                           ('Posición vertical (0–100 %)', self.idle_total_y_var),
                           ('Opacidad (30–100 %)', self.idle_total_alpha_var)]:
            line = ttk.Frame(box_idle)
            line.pack(fill='x', pady=4)
            ttk.Label(line, text=title, width=30).pack(side='left')
            ttk.Scale(line, from_=30 if var is self.idle_total_alpha_var else 0, to=100,
                      variable=var, orient='horizontal', length=300).pack(side='left', padx=6)
            ttk.Label(line, textvariable=var, width=4).pack(side='left')
        ttk.Label(box_idle, text='Está sincronizado con el aviso grande: ambos usan EL MISMO cálculo y el mismo segundo OCR.', foreground=GOLD_TEXT).pack(anchor='w')
        ttk.Label(box_idle, text='Para usarlo, calibra la zona del reloj y activa el OCR. En el modo global solo mide los intervalos sin aldeanos en la cola visible; no identifica TCs independientes.',
                  wraplength=660, foreground=GOLD_TEXT).pack(anchor='w', pady=6)
        row_test = ttk.Frame(box_idle)
        row_test.pack(fill='x', pady=8)
        ttk.Button(row_test, text='Probar contador durante 15 s', command=self.test_total).pack(side='left')
        ttk.Button(row_test, text='Reiniciar acumulado ahora', command=self.reset_accumulated).pack(side='left', padx=9)
        ttk.Label(box_idle, text='Acumulado actual:').pack(anchor='w', pady=(10, 0))
        ttk.Label(box_idle, textvariable=self.idle_total_text_var, font=('Consolas', 24, 'bold')).pack(anchor='w')


        era = ttk.LabelFrame(age_tab, text='IDLE TC por edad de la partida',padding=12)
        era.pack(fill='x',pady=6)
        ttk.Checkbutton(era,text='Mostrar ventana flotante de IDLE por edades',
                        variable=self.age_overlay_on_var, command=self.apply_age_overlay).pack(anchor='w',pady=5)
        ttk.Label(era,text='Alta Edad Media → Edad Feudal → Edad de los Castillos → Edad Imperial. '
                  'Cada edad termina cuando escudo o texto confirman la siguiente. '
                  'Se emplea el mismo acumulado IDLE del reloj de partida.',
                  wraplength=670).pack(anchor='w',pady=(2,7))
        ttk.Button(era,text='Calibrar escudo de edad',command=self.calibrate_age).pack(anchor='w')
        ttk.Button(era,text='Calibrar texto de edad (respaldo)',command=self.calibrate_age_text).pack(anchor='w',pady=4)
        ttk.Label(era,textvariable=self.current_age_var,foreground=GOLD_TEXT,
                  wraplength=650).pack(anchor='w',pady=7)
        r = ttk.Frame(era);r.pack(fill='x',pady=5)
        ttk.Label(r,text='Monitor del display:').pack(side='left')
        self.age_monitor_box = ttk.Combobox(r,textvariable=self.age_monitor_var,
                                           state='readonly',width=36)
        self.age_monitor_box.pack(side='left',padx=7)
        ttk.Button(r,text='Actualizar',command=self.refresh_age_monitors).pack(side='left')
        self.refresh_age_monitors()
        resize=ttk.Frame(era);resize.pack(fill='x',pady=5)
        ttk.Label(resize,text='Tamaño del display (50–180 %):').pack(side='left')
        tk.Scale(resize,from_=50,to=180,resolution=5,variable=self.age_scale_var,
                 orient='horizontal',showvalue=False,length=250,highlightthickness=0).pack(side='left')
        ttk.Label(resize,textvariable=self.age_scale_var,width=4).pack(side='left')
        ttk.Label(resize,text='%').pack(side='left')
        for title,var in [('Horizontal (0–100 %)',self.age_x_var),
                          ('Vertical (0–100 %)',self.age_y_var),
                          ('Opacidad (30–100 %)',self.age_alpha_var)]:
            r=ttk.Frame(era);r.pack(fill='x',pady=4)
            ttk.Label(r,text=title,width=27).pack(side='left')
            ttk.Scale(r,from_=30 if var is self.age_alpha_var else 0,to=100,
                      variable=var,orient='horizontal',length=300).pack(side='left',padx=6)
            ttk.Label(r,textvariable=var,width=4).pack(side='left')
        row_era = ttk.Frame(era);row_era.pack(fill='x',pady=8)
        ttk.Button(row_era,text='Probar display (15 s)',
                   command=self.test_ages).pack(side='left')
        ttk.Button(row_era,text='Aplicar posición',command=self.apply_age_overlay).pack(side='left',padx=6)
        ttk.Button(row_era,text='Exportar resumen CSV…',command=self.export_age_csv).pack(side='left')
        ttk.Label(era,text='Las edades no observadas mostrarán --:--. '
                  'El OCR del reloj es obligatorio; puedes calibrar escudo, texto o ambos. '
                  'Recalibra si cambias la escala del HUD.',
                  foreground=GOLD_TEXT,wraplength=660).pack(anchor='w')

        control_box=ttk.LabelFrame(age_tab,text='Mandos flotantes: sonido, pausa y mostrar/ocultar displays',padding=12)
        control_box.pack(fill='x',pady=8)
        ttk.Checkbutton(control_box,text='Mostrar botones flotantes sobre el juego (independientes del display de edades)',
                        variable=self.control_on_var,command=self.apply_control_overlay).pack(anchor='w',pady=4)
        ttk.Label(control_box,text='Pausar el avisador detiene el cálculo y los avisos, pero no pausa Age of Empires. '
                  'Al reanudar, el reloj del juego vuelve a ser la única referencia.',
                  wraplength=680).pack(anchor='w',pady=3)
        ttk.Label(control_box, text='Tres flechas: ← aviso izquierdo, ↑ contador superior y → edades de la derecha. Ocultar no borra estadísticas.',
                  wraplength=660, foreground=GOLD_TEXT).pack(anchor='w', pady=3)
        mrow=ttk.Frame(control_box);mrow.pack(fill='x',pady=5)
        ttk.Label(mrow,text='Monitor de los botones:').pack(side='left')
        self.control_monitor_box=ttk.Combobox(mrow,textvariable=self.control_monitor_var,
                                              state='readonly',width=35)
        self.control_monitor_box.pack(side='left',padx=7)
        ttk.Button(mrow,text='Actualizar',command=self.refresh_control_monitors).pack(side='left')
        self.refresh_control_monitors()
        resize=ttk.Frame(control_box);resize.pack(fill='x',pady=5)
        ttk.Label(resize,text='Tamaño del display (50–180 %):').pack(side='left')
        tk.Scale(resize,from_=50,to=180,resolution=5,variable=self.control_scale_var,
                 orient='horizontal',showvalue=False,length=250,highlightthickness=0).pack(side='left')
        ttk.Label(resize,textvariable=self.control_scale_var,width=4).pack(side='left')
        ttk.Label(resize,text='%').pack(side='left')
        for title,var in [('Horizontal (0–100 %)',self.control_x_var),
                          ('Vertical (0–100 %)',self.control_y_var),
                          ('Opacidad (30–100 %)',self.control_opacity_var)]:
            r=ttk.Frame(control_box);r.pack(fill='x',pady=3)
            ttk.Label(r,text=title,width=27).pack(side='left')
            ttk.Scale(r,from_=30 if var is self.control_opacity_var else 0,to=100,
                      variable=var,orient='horizontal',length=300).pack(side='left',padx=6)
            ttk.Label(r,textvariable=var,width=4).pack(side='left')
        test_row=ttk.Frame(control_box);test_row.pack(fill='x',pady=5)
        ttk.Button(test_row,text='Mostrar/probar mandos',command=self.test_control_overlay).pack(side='left')
        ttk.Button(test_row,text='Aplicar posición',command=self.apply_control_overlay).pack(side='left',padx=7)
        ttk.Button(test_row,text='Cerrar prueba',command=self.close_control_preview).pack(side='left')
        ttk.Label(control_box,text='← aviso izquierdo · ↑ contador superior · → edades derecha · 🔊/🔇 audio · Ⅱ/▶ pausa. Botón elevado: visible. Botón hundido: oculto.',wraplength=680).pack(anchor='w')

        # Display opcional e independiente por edades.
        controls = ttk.Frame(pad)
        controls.pack(fill='x', pady=10)
        self.start_button = ttk.Button(controls, text='▶ Iniciar monitorización', command=self.start)
        self.start_button.pack(side='left', padx=(0, 8))
        self.stop_button = ttk.Button(controls, text='■ Detener', command=self.stop, state='disabled')
        self.stop_button.pack(side='left')
        self.mute_button = ttk.Button(controls,text='Silenciar',command=self.toggle_mute)
        self.mute_button.pack(side='left',padx=(12,4))
        self.manual_pause_button = ttk.Button(controls,text='Pausar avisador',command=self.toggle_manual_pause)
        self.manual_pause_button.pack(side='left',padx=4)
        ttk.Button(controls, text='Guardar preferencias', command=self.save_preferences).pack(side='right')
        ttk.Label(pad, textvariable=self.status_var, font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(pad, textvariable=self.details_var, wraplength=730).pack(anchor='w', pady=4)
        # El registro también tiene su propia barra de desplazamiento.
        log_frame = ttk.Frame(pad)
        log_frame.pack(fill='both', expand=True, pady=5)
        log_bar = ttk.Scrollbar(log_frame, orient='vertical')
        log_bar.pack(side='right', fill='y')
        self.logbox = tk.Text(log_frame, height=5, font=('Consolas', 9),
                              state='disabled', wrap='word', bg=PARCHMENT_LIGHT, fg=GOLD_TEXT,
                              relief='flat', highlightthickness=2,
                              highlightbackground=GOLD_BORDER, highlightcolor=GOLD_BORDER,
                              yscrollcommand=log_bar.set)
        self.logbox.pack(side='left', fill='both', expand=True)
        log_bar.configure(command=self.logbox.yview)

    def _on_mouse_wheel(self, event):
        """Desplaza solo la pestaña visible cuando el cursor está sobre ella."""
        try:
            selected = self.tabs.select()
            if not selected:
                return
            page = self.tabs.nametowidget(selected)
            # Evita capturar la rueda sobre el log o el aviso flotante.
            if not str(event.widget).startswith(str(page)):
                return
            page.wheel(event)
            return 'break'
        except (tk.TclError, AttributeError):
            return

    def refresh_visual_monitors(self):
        """Lista monitores físicos y sus posiciones en el escritorio virtual."""
        previous = int(self.config.get('visual_monitor', 1))
        if self.visual_monitor_var.get() in self.visual_monitor_map:
            previous = self.visual_monitor_map[self.visual_monitor_var.get()]
        with mss.mss() as sct:
            monitors = sct.monitors[1:]
        self.visual_monitor_map = {
            f'Monitor {n} — {m["width"]}×{m["height"]} (X={m["left"]}, Y={m["top"]})': n
            for n, m in enumerate(monitors, 1)
        }
        labels = list(self.visual_monitor_map)
        self.visual_monitor_box['values'] = labels
        if labels:
            chosen = next((label for label, n in self.visual_monitor_map.items() if n == previous), labels[0])
            self.visual_monitor_var.set(chosen)
        else:
            self.visual_monitor_var.set('No se detectan monitores')

    def refresh_idle_monitors(self):
        previous = int(self.config.get('idle_total_monitor', 1))
        if self.idle_total_monitor_var.get() in self.idle_total_monitor_map:
            previous = self.idle_total_monitor_map[self.idle_total_monitor_var.get()]
        with mss.mss() as sct:
            mons = sct.monitors[1:]
        self.idle_total_monitor_map = {
            f'Monitor {n} — {m["width"]}×{m["height"]} (X={m["left"]}, Y={m["top"]})': n
            for n, m in enumerate(mons, 1)
        }
        self.idle_total_monitor_box['values'] = list(self.idle_total_monitor_map)
        key = next((k for k,v in self.idle_total_monitor_map.items() if v == previous),
                   next(iter(self.idle_total_monitor_map), ''))
        self.idle_total_monitor_var.set(key)


    def refresh_age_monitors(self):
        selected = int(self.config.get('edades_monitor',1))
        if self.age_monitor_var.get() in self.age_monitor_map:
            selected = self.age_monitor_map[self.age_monitor_var.get()]
        with mss.mss() as sct:
            physical = sct.monitors[1:]
        self.age_monitor_map = {
            f'Monitor {idx} — {m["width"]}×{m["height"]} (X={m["left"]}, Y={m["top"]})':idx
            for idx,m in enumerate(physical,1)
        }
        self.age_monitor_box['values'] = list(self.age_monitor_map)
        self.age_monitor_var.set(next((key for key,val in self.age_monitor_map.items()
                                      if val==selected),next(iter(self.age_monitor_map),'')))

    def refresh_control_monitors(self):
        selected=int(self.config.get('controles_monitor',1))
        if self.control_monitor_var.get() in self.control_monitor_map:
            selected=self.control_monitor_map[self.control_monitor_var.get()]
        with mss.mss() as sct:
            monitors=sct.monitors[1:]
        self.control_monitor_map={
            f'Monitor {n} — {m["width"]}×{m["height"]} (X={m["left"]}, Y={m["top"]})':n
            for n,m in enumerate(monitors,1)}
        self.control_monitor_box['values']=list(self.control_monitor_map)
        self.control_monitor_var.set(next((name for name,n in self.control_monitor_map.items()
                                        if n==selected),next(iter(self.control_monitor_map),'')))

    def control_overlay_config(self):
        selected=self.control_monitor_var.get()
        if selected not in self.control_monitor_map:
            raise ValueError('Selecciona monitor para los botones de control.')
        return {'controles_visible':bool(self.control_on_var.get()),
                'controles_monitor':self.control_monitor_map[selected],
                'controles_pos_x':int(self.control_x_var.get()),
                'controles_pos_y':int(self.control_y_var.get()),
                'controles_opacidad':int(self.control_opacity_var.get()),
                'controles_escala':int(self.control_scale_var.get())}

    def apply_control_overlay(self):
        try:
            options=self.control_overlay_config()
            self.config.update(options)
            self.save()
            if self.running_settings is not None:
                self.running_settings.update(options)
            if options['controles_visible']:
                self.game_controls.show_controls(options)
            else:
                self.game_controls.hide()
            self.sync_visibility_buttons()
        except Exception as exc:
            messagebox.showerror('Botones flotantes',str(exc))

    @staticmethod
    def _age_preview_snapshot():
        return {'age':'castillos', 'seen':['oscura','feudal','castillos'],
            'values':{'oscura':25,'feudal':35,'castillos':15,'imperial':0},
            'lost_by_age':{'oscura':1,'feudal':1,'castillos':1,'imperial':0},
            'unassigned':0,'unassigned_lost':0,'lost_total':3,'total':75}

    def test_control_overlay(self):
        """Vista previa de los tres paneles + controles, sin tener AoE2 abierto."""
        if self.thread and self.thread.is_alive():
            self.apply_control_overlay()
            return
        try:
            self.preview_controls_active=True
            self.control_on_var.set(True)
            self.config.update(self.visual_config())
            self.config.update(self.total_idle_config())
            self.config.update(self.age_overlay_config())
            self.apply_control_overlay()
            self.total_idle_overlay.update_total(75)
            self.age_idle_overlay.update_ages(self._age_preview_snapshot())
            self.visual_alert.update_metrics((75,3))
            if self.idle_total_on_var.get():
                self.total_idle_overlay.show_total(self.config)
            if self.age_overlay_on_var.get():
                self.age_idle_overlay.show_ages(self.config)
            if self.visual_enabled_var.get():
                self.visual_alert.show(self.config)
                self.visual_alert.update_metrics((75,3))
            self.log('VISTA PREVIA: usa ↑ ← → para ocultar o mostrar los paneles.')
        except Exception as exc:
            messagebox.showerror('Prueba de mandos',str(exc))

    def close_control_preview(self):
        self.preview_controls_active=False
        if self.running_settings is None:
            self.visual_alert.hide()
            self.total_idle_overlay.hide()
            self.age_idle_overlay.hide()
            self.game_controls.hide()

    def sync_visibility_buttons(self):
        self.game_controls.update_visibility({
            'total':self.idle_total_on_var.get(),
            'visual':self.visual_enabled_var.get(),
            'ages':self.age_overlay_on_var.get(),
        })

    def toggle_overlay_visibility(self, part, from_ui=False):
        """Llamada desde botones flotantes o el checkbox de aviso visual.

        Las zonas y las cifras IDLE se mantienen aunque el HUD se oculte.
        """
        try:
            if part == 'total':
                if not from_ui:
                    self.idle_total_on_var.set(not self.idle_total_on_var.get())
                enabled=bool(self.idle_total_on_var.get())
                self.config['idle_total_visible']=enabled
                if self.running_settings is not None:
                    self.running_settings['idle_total_visible']=enabled
                if self.running_settings is not None or self.preview_controls_active:
                    if enabled:
                        if self.preview_controls_active and self.running_settings is None:
                            self.total_idle_overlay.update_total(75)
                        self.total_idle_overlay.show_total(self.running_settings or self.config)
                    else:
                        self.total_idle_overlay.hide()
                self.log(('Mostrado' if enabled else 'Ocultado')+' contador IDLE TC.')
            elif part == 'ages':
                if not from_ui:
                    self.age_overlay_on_var.set(not self.age_overlay_on_var.get())
                enabled=bool(self.age_overlay_on_var.get())
                if enabled and self.thread and self.thread.is_alive() and not (self.config.get('zona_edad') or self.config.get('zona_edad_texto')):
                    self.age_overlay_on_var.set(False)
                    raise ValueError('Calibra el escudo y/o el texto de edad antes de mostrar el display.')
                self.config['edades_visible']=enabled
                if self.running_settings is not None:
                    self.running_settings['edades_visible']=enabled
                if self.running_settings is not None or self.preview_controls_active:
                    if enabled:
                        if self.preview_controls_active and self.running_settings is None:
                            self.age_idle_overlay.update_ages(self._age_preview_snapshot())
                        self.age_idle_overlay.show_ages(self.running_settings or self.config)
                    else:
                        self.age_idle_overlay.hide()
                self.log(('Mostrado' if enabled else 'Ocultado')+' display por edades.')
            elif part == 'visual':
                if not from_ui:
                    self.visual_enabled_var.set(not self.visual_enabled_var.get())
                enabled=bool(self.visual_enabled_var.get())
                self.config['mostrar_aviso_visual']=enabled
                if self.running_settings is not None:
                    self.running_settings['mostrar_aviso_visual']=enabled
                if not enabled:
                    self.visual_alert.hide()
                elif self.preview_controls_active and self.running_settings is None:
                    self.visual_alert.show(self.config)
                    self.visual_alert.update_metrics((75,3))
                self.log(('Habilitado' if enabled else 'Ocultado')+' aviso visual de alerta.')
            else:
                raise ValueError('Display desconocido: '+str(part))
            self.save()
        except Exception as exc:
            self.log('No se pudo cambiar la visibilidad: '+str(exc))
            messagebox.showwarning('Visibilidad',str(exc))
        finally:
            self.sync_visibility_buttons()

    def toggle_mute(self):
        if self.muted_event.is_set():
            self.muted_event.clear()
            message='Sonido ACTIVADO'
        else:
            self.muted_event.set()
            self.sound_engine.stop_sound(include_celebration=True)
            message='Sonido SILENCIADO'
        self.mute_button.config(text='Activar sonido' if self.muted_event.is_set() else 'Silenciar')
        self.game_controls.update_buttons(self.muted_event.is_set(),self.manual_pause_event.is_set())
        self.log(message)

    def toggle_manual_pause(self):
        if self.manual_pause_event.is_set():
            self.manual_pause_event.clear()
            message='Avisador REANUDADO'
        else:
            self.manual_pause_event.set()
            self.finish_celebration()
            self.sound_engine.stop_sound(include_celebration=True)
            self.visual_alert.hide()
            message='Avisador en PAUSA MANUAL (el juego no se pausa)'
        self.manual_pause_button.config(text='Reanudar avisador' if self.manual_pause_event.is_set() else 'Pausar avisador')
        self.game_controls.update_buttons(self.muted_event.is_set(),self.manual_pause_event.is_set())
        self.log(message)

    def age_overlay_config(self):
        name=self.age_monitor_var.get()
        if name not in self.age_monitor_map:
            raise ValueError('Selecciona el monitor del IDLE por edades.')
        return {'edades_visible':self.age_overlay_on_var.get(),
                'edades_monitor':self.age_monitor_map[name],
                'edades_pos_x':int(self.age_x_var.get()),
                'edades_pos_y':int(self.age_y_var.get()),
                'edades_opacidad':int(self.age_alpha_var.get()),
                'edades_escala':int(self.age_scale_var.get())}

    def test_ages(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo('Prueba','Detén la monitorización antes de probar el display.')
            return
        opts=self.age_overlay_config()
        self.config.update(opts)
        self.save()
        self.age_idle_overlay.update_ages({'age':'castillos',
             'seen':['oscura','feudal','castillos'],
             'values':{'oscura':65,'feudal':104,'castillos':37,'imperial':0},
             'lost_by_age':{'oscura':2,'feudal':4,'castillos':2,'imperial':0},
             'unassigned':0,'unassigned_lost':0,'lost_total':8,'total':206})
        self.age_idle_overlay.show_ages(opts)
        self.root.after(15000,lambda:self.age_idle_overlay.hide()
                        if self.running_settings is None else None)

    def apply_age_overlay(self):
        """Permite mostrar/ocultar/mover las edades sin reiniciar la partida."""
        try:
            opts = self.age_overlay_config()
            if opts['edades_visible'] and self.thread and self.thread.is_alive() and not (self.config.get('zona_edad') or self.config.get('zona_edad_texto')):
                self.age_overlay_on_var.set(False)
                raise ValueError('Calibra la zona de la edad antes de activarla.')
            self.config.update(opts)
            self.save()
            if not opts['edades_visible']:
                self.age_idle_overlay.hide()
            elif self.thread and self.thread.is_alive() and self.running_settings is not None:
                self.running_settings.update(opts)
                self.age_idle_overlay.show_ages(opts)
            self.sync_visibility_buttons()
        except Exception as exc:
            messagebox.showerror('IDLE por edades',str(exc))

    def export_age_csv(self):
        """Exporta el desglose con edades desconocidas sin inventar segundos."""
        snap=self.last_age_snapshot
        if snap is None and AGE_CURRENT_FILE.is_file():
            try:
                snap=json.loads(AGE_CURRENT_FILE.read_text(encoding='utf-8'))['edades']
            except Exception:
                pass
        if snap is None:
            messagebox.showinfo('Resumen','Todavía no hay registros de IDLE por edades.')
            return
        filepath=filedialog.asksaveasfilename(parent=self.root,defaultextension='.csv',
            initialfile='idle_tc_edades.csv',filetypes=[('Archivo CSV','*.csv')])
        if not filepath:
            return
        import csv
        with open(filepath,'w',newline='',encoding='utf-8-sig') as handle:
            writer=csv.writer(handle,delimiter=';')
            writer.writerow(['Edad','Segundos IDLE TC','Formato','Aldeanos no creados','Estado'])
            for age in AGE_ORDER:
                seen=age in snap.get('seen',[])
                val=snap.get('values',{}).get(age,0) if seen else ''
                writer.writerow([AGE_NAMES[age],val,
                                 format_game_duration(val) if seen else '',
                                 snap.get('lost_by_age',{}).get(age,0) if seen else '',
                                 'actual' if age==snap.get('age') else ('registrada' if seen else 'sin datos')])
            writer.writerow(['Sin edad identificada',snap.get('unassigned',0),
                             format_game_duration(snap.get('unassigned',0)),
                             snap.get('unassigned_lost',0),'sin asignar'])
            writer.writerow(['IDLE TC total',snap.get('total',0),
                             format_game_duration(snap.get('total',0)),
                             snap.get('lost_total',0),'juego'])
        self.log('Resumen exportado: '+filepath)

    def calibrate_age(self):
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Edad','Detén primero la monitorización.')
            return
        try:
            mon=self.monitor_id()
            messagebox.showinfo('Calibrar edad',
                'Deja visible el ESCUDO circular de la edad (I, II, III o IV).\n\n'
                'Al aceptar, vuelve al juego para capturar en 4 segundos. '
                'Marca SOLO el escudo, lo más ajustado posible; NO incluyas texto, reloj ni HUD.')
            self.root.withdraw()
            try:
                time.sleep(4)
                with mss.mss() as sct:
                    frame=grab_monitor(sct,mon)
                rect=choose_rect('SELECCIONA SOLO EL ESCUDO (I–IV) - ENTER',frame)
                x,y,w,h=rect
                age,score=detect_game_age(frame[y:y+h,x:x+w],load_age_signatures())
                if age is None:
                    raise ValueError('No se pudo reconocer el escudo. '
                                     f'Confianza máxima {score:.2f}; incluye solamente la insignia I, II, III o IV.')
                self.config['zona_edad']=rect
                self.config['version_detector_edad']=26
                self.config['monitor']=mon
                self.save()
                self.refresh_calib_label()
                self.current_age_var.set('Calibrado: '+AGE_NAMES[age]+f' · confianza {score:.2f}')
                self.log('Calibrada edad '+AGE_NAMES[age]+f', similitud {score:.2f}')
            finally:
                cv2.destroyAllWindows()
                self.root.deiconify()
                self.root.lift()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Calibración de edad',str(exc))

    def calibrate_age_text(self):
        """Una segunda zona independiente; no sobrescribe el escudo existente."""
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Edad por texto', 'Detén antes la monitorización.')
            return
        try:
            mon = self.monitor_id()
            messagebox.showinfo('Edad por texto',
                'Abre una partida con el nombre de la edad visible.\n\n'
                'Tras aceptar tienes 4 segundos para volver al juego.\n'
                'Selecciona el TEXTO COMPLETO (por ejemplo «Alta Edad Media»), '
                'sin incluir el escudo ni el reloj. Funciona con texto blanco o amarillo.')
            self.root.withdraw()
            try:
                time.sleep(4)
                with mss.mss() as sct:
                    frame = grab_monitor(sct, mon)
                rect = choose_rect('SELECCIONA EL TEXTO DE EDAD - ENTER', frame)
                x,y,w,h = rect
                age, score = detect_game_age_text(frame[y:y+h,x:x+w])
                # Guardamos incluso si la lectura inicial no se reconoce: el
                # OCR puede mejorar cuando cambie el escenario y el color.
                self.config['zona_edad_texto'] = rect
                self.config['version_detector_edad'] = 26
                self.config['monitor'] = mon
                self.save()
                self.refresh_calib_label()
                if age:
                    detail = AGE_NAMES[age] + f' (confianza {score:.2f})'
                else:
                    detail = 'zona guardada; lectura inicial incierta'
                self.current_age_var.set('Texto calibrado: ' + detail)
                self.log('Calibración de texto: ' + detail)
            finally:
                cv2.destroyAllWindows()
                self.root.deiconify()
                self.root.lift()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Calibración del texto', str(exc))

    def total_idle_config(self):
        name = self.idle_total_monitor_var.get()
        if name not in self.idle_total_monitor_map:
            raise ValueError('Selecciona el monitor del contador acumulado.')
        return {'idle_total_visible': bool(self.idle_total_on_var.get()),
                'idle_total_monitor': self.idle_total_monitor_map[name],
                'idle_total_pos_x': int(self.idle_total_x_var.get()),
                'idle_total_pos_y': int(self.idle_total_y_var.get()),
                'idle_total_opacidad': int(self.idle_total_alpha_var.get()),
                'idle_total_escala': int(self.idle_total_scale_var.get())}

    def test_total(self):
        if self.running_settings is not None:
            messagebox.showinfo('Prueba', 'Detén antes la monitorización para probar el contador.')
            return
        options = self.total_idle_config()
        self.config.update(options)
        self.save()
        self.total_idle_overlay.update_total(143)
        self.total_idle_overlay.show_total(options)
        self.root.after(15000, lambda: self.total_idle_overlay.hide()
                        if self.running_settings is None else None)

    def reset_accumulated(self):
        if self.thread and self.thread.is_alive():
            self.reset_total_event.set()
        else:
            self.total_idle_overlay.update_total(0)
            self.idle_total_text_var.set('00:00')
        self.log('Se ha solicitado reiniciar el acumulado de IDLE TC.')





    def export_age_csv(self):
        """Exporta el desglose con edades desconocidas sin inventar segundos."""
        snap=self.last_age_snapshot
        if snap is None and AGE_CURRENT_FILE.is_file():
            try:
                snap=json.loads(AGE_CURRENT_FILE.read_text(encoding='utf-8'))['edades']
            except Exception:
                pass
        if snap is None:
            messagebox.showinfo('Resumen','Todavía no hay registros de IDLE por edades.')
            return
        filepath=filedialog.asksaveasfilename(parent=self.root,defaultextension='.csv',
            initialfile='idle_tc_edades.csv',filetypes=[('Archivo CSV','*.csv')])
        if not filepath:
            return
        import csv
        with open(filepath,'w',newline='',encoding='utf-8-sig') as handle:
            writer=csv.writer(handle,delimiter=';')
            writer.writerow(['Edad','Segundos IDLE TC','Formato','Aldeanos no creados','Estado'])
            for age in AGE_ORDER:
                seen=age in snap.get('seen',[])
                val=snap.get('values',{}).get(age,0) if seen else ''
                writer.writerow([AGE_NAMES[age],val,
                                 format_game_duration(val) if seen else '',
                                 snap.get('lost_by_age',{}).get(age,0) if seen else '',
                                 'actual' if age==snap.get('age') else ('registrada' if seen else 'sin datos')])
            writer.writerow(['Sin edad identificada',snap.get('unassigned',0),
                             format_game_duration(snap.get('unassigned',0)),
                             snap.get('unassigned_lost',0),'sin asignar'])
            writer.writerow(['IDLE TC total',snap.get('total',0),
                             format_game_duration(snap.get('total',0)),
                             snap.get('lost_total',0),'juego'])
        self.log('Resumen exportado: '+filepath)


    def selected_visual_monitor(self):
        label = self.visual_monitor_var.get()
        if label not in self.visual_monitor_map:
            raise ValueError('Selecciona un monitor válido para el aviso visual.')
        return self.visual_monitor_map[label]

    def visual_config(self):
        return {**{name: value.get() for name, value in self.hud_appearance_vars.items()},
                'canal_aviso': self.channel_var.get(),
                'mostrar_aviso_visual': bool(self.visual_enabled_var.get()),
                'imagen_visual': self.visual_file_var.get().strip(),
                'visual_tamano': int(self.visual_size_var.get()),
                'visual_escala': int(self.visual_scale_var.get()),
                'visual_alerta_grande': bool(self.visual_big_var.get()),
                'visual_esquina': self.visual_corner_var.get(),
                'visual_monitor': self.selected_visual_monitor(),
                'visual_posicion_libre': bool(self.visual_free_var.get()),
                'visual_pos_x': int(self.visual_x_var.get()),
                'visual_pos_y': int(self.visual_y_var.get()),
                'visual_opacidad': int(self.visual_opacity_var.get()),
                'mostrar_perdidas': bool(self.losses_var.get())}

    def choose_hud_color(self, name):
        variable = self.hud_appearance_vars[name]
        _, color = colorchooser.askcolor(color=variable.get(), parent=self.root)
        if color:
            variable.set(color)
            if name == 'marco_color_fondo':
                self.hud_appearance_vars['marco_fondo'].set('color')
            self.save_preferences()

    def choose_visual(self):
        path = filedialog.askopenfilename(parent=self.root, title='Imagen para el aviso',
            filetypes=[('Imagen', '*.png *.jpg *.jpeg *.webp *.bmp'),('Todos', '*.*')])
        if path:
            try:
                with Image.open(path) as img:
                    img.verify()
                self.visual_file_var.set(path)
                self.save_preferences()
            except Exception as exc:
                messagebox.showerror('Imagen', str(exc))

    def reset_visual(self):
        self.visual_file_var.set('')
        self.save_preferences()

    def create_idle_goals(self, tab):
        panel = ttk.LabelFrame(tab, text='Objetivo de IDLE por edad', padding=12)
        panel.pack(fill='x', pady=6)
        ttk.Label(panel, text='Introduce el límite en segundos. Deja el campo vacío para omitir esa edad.',
                  wraplength=620).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 8))
        saved = self.config.get('objetivos_idle') or {}
        self.goal_vars = {}
        for row, age in enumerate(AGE_ORDER, 1):
            variable = tk.StringVar(value=saved.get(age, ''))
            self.goal_vars[age] = variable
            ttk.Label(panel, text=AGE_NAMES[age]).grid(row=row, column=0, sticky='w', pady=4)
            ttk.Entry(panel, width=9, textvariable=variable).grid(row=row, column=1, padx=10)
            ttk.Label(panel, text='s').grid(row=row, column=2, sticky='w')
        ttk.Label(tab, text='Para Imperial, pulsa «Comprobar fin de Imperial» cuando termine la partida.',
                  wraplength=620).pack(anchor='w', pady=(3, 8))
        actions = ttk.Frame(tab)
        actions.pack(anchor='w')
        ttk.Button(actions, text='Guardar objetivos', command=self.save_preferences).pack(side='left', padx=(0, 6))
        ttk.Button(actions, text='Probar felicitación', command=self.test_celebration).pack(side='left', padx=6)
        ttk.Button(actions, text='Probar objetivo no logrado',
                   command=lambda: self.test_celebration(False)).pack(side='left', padx=6)
        ttk.Button(actions, text='Comprobar fin de Imperial',
                   command=self.check_imperial_goal).pack(side='left', padx=6)

    def idle_goals(self):
        goals = {}
        for age, variable in self.goal_vars.items():
            value = variable.get().strip()
            if not value:
                continue
            try:
                seconds = int(value)
                if seconds < 1:
                    raise ValueError
            except ValueError:
                raise ValueError(f'{AGE_NAMES[age]} necesita un objetivo en segundos enteros, mayor que cero.') from None
            goals[age] = seconds
        return goals

    def celebration_settings(self, options):
        return dict(options, imagen_visual=str(BASE / GOAL_PORTRAIT), mostrar_perdidas=False,
                    objetivo_cumplido=self.goal_achieved, texto_objetivo=self.goal_banner)

    def show_celebration(self, options, achieved=True):
        self.finish_celebration()
        self.goal_achieved = achieved
        if achieved:
            self.goal_banner = random.choice(GOAL_BANNERS)
        self.visual_alert.show(self.celebration_settings(options))
        self.celebration_job = self.root.after(GOAL_DURATION_MS, self.finish_celebration, True)
        if not self.muted_event.is_set():
            try:
                clip = random.choice(GOAL_SOUNDS) if achieved else MISSED_GOAL_SOUND
                self.sound_engine.play_celebration(clip, options['volumen'])
            except (OSError, pygame.error) as exc:
                self.log(f'No se pudo reproducir la felicitación: {exc}')

    def finish_celebration(self, restore=False):
        if self.celebration_job is None:
            return
        self.root.after_cancel(self.celebration_job)
        self.celebration_job = None
        if restore:
            self.render_visual_snapshot()
        else:
            self.visual_alert.hide()

    def render_visual_snapshot(self):
        payload = self.latest_visual_snapshot
        if (self.running_settings is not None and payload and payload['show_visual'] and
                self.visual_enabled_var.get() and not self.stop_event.is_set() and
                not self.manual_pause_event.is_set()):
            self.visual_alert.show(self.running_settings)
            self.visual_alert.update_metrics(payload['visual_metrics'])
        else:
            self.visual_alert.hide()

    def test_celebration(self, achieved=True):
        try:
            self.show_celebration({**self.visual_config(), **self.audio_config()}, achieved)
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror('Probar aviso de objetivo', str(exc), parent=self.root)

    def check_idle_goal(self, age, elapsed):
        goal = self.running_settings.get('objetivos_idle', {}).get(age)
        if goal is None:
            return None
        self.log(f'{AGE_NAMES[age]} · IDLE {format_game_duration(elapsed)} · '
                 f'objetivo inferior a {format_game_duration(goal)}.')
        achieved = elapsed < goal
        self.show_celebration(self.running_settings, achieved)
        return achieved

    def check_imperial_goal(self):
        snapshot = self.last_age_snapshot
        if not self.running_settings or not snapshot or snapshot['age'] != 'imperial':
            messagebox.showinfo('Objetivo Imperial', 'Todavía no se ha registrado la Edad Imperial en la partida activa.',
                                parent=self.root)
            return
        if self.imperial_checked:
            self.log('El objetivo de Imperial ya se ha comprobado en esta partida.')
            return
        result = self.check_idle_goal('imperial', snapshot['values']['imperial'])
        if result is None:
            messagebox.showinfo('Objetivo Imperial', 'Guarda primero un objetivo para Imperial.', parent=self.root)
            return
        self.imperial_checked = True

    def test_visual(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo('Vista previa', 'Detén la monitorización para probar el aviso.')
            return
        self.finish_celebration()
        self.sound_engine.stop_sound(include_celebration=True)
        options = self.visual_config()
        self.config.update(options)
        self.save()
        self.visual_alert.show(options)
        self.visual_alert.update_metrics((75, 3))
        if self.channel_var.get() != 'visual' and not self.muted_event.is_set():
            self.sound_engine.play(self.audio_config())
        self.log('Prueba visual V21: monitor elegido '+str(options.get('visual_monitor'))+'. Puedes consultar las coordenadas reales en el registro. Cambia a AoE2.')
        self.root.after(15000, lambda: self.visual_alert.hide()
                        if self.running_settings is None and self.celebration_job is None else None)

    def select_sound(self):
        chosen = filedialog.askopenfilename(title='Selecciona tu aviso MP3/WAV',
                    filetypes=[('Audio compatible', '*.mp3 *.wav'), ('MP3', '*.mp3'), ('WAV', '*.wav')],
                    parent=self.root)
        if chosen:
            self.custom_file_var.set(chosen)
            self.sound_var.set('archivo')
            self.save_preferences()

    def audio_config(self):
        return {'sonido': self.sound_var.get(), 'archivo_sonido': self.custom_file_var.get(),
                'volumen': int(self.volume_var.get()), 'voz': 'Crea aldeanos'}

    def test_sound(self):
        setting = self.audio_config()
        if setting['sonido'] == 'archivo' and not Path(setting['archivo_sonido']).is_file():
            messagebox.showwarning('Audio', 'Selecciona primero un archivo MP3 o WAV.')
            return
        if not self.muted_event.is_set():
            self.sound_engine.play(setting)

    def save_preferences(self):
        try:
            self.config['objetivos_idle'] = self.idle_goals()
            self.config.update({'monitor': int(self.monitor_var.get())})
            self.config.update(self.audio_config())
            self.config.update(self.visual_config())
            self.config.update(self.total_idle_config())
            self.config.update(self.age_overlay_config())
            self.config.update(self.control_overlay_config())
            self.config['rojo_activo']=bool(self.red_on_var.get())
            self.config['tecnologias_activo']=bool(self.technology_on_var.get())
            self.config.update({'limite_tiempo_activo': self.limit_time_on_var.get(),
                                'limite_aldeanos_activo': self.limit_pop_on_var.get(),
                                'limite_minutos': float(self.limit_time_var.get()),
                                'limite_aldeanos': int(self.limit_pop_var.get()),
                                'repeticion': float(self.repeat_var.get()),
                                'solo_juego_activo': self.foreground_var.get(),
                                'reiniciar_al_reloj_cero': self.auto_restart_var.get(),
                                'visual_permanencia': int(float(self.hold_var.get().replace(',', '.'))),
                                'ocr_intervalo': float(self.ocr_interval_var.get().replace(',', '.')),
                                'filtro_parpadeo_segundos': int(self.flicker_filter_var.get())})
            if not 1 <= self.config['repeticion'] <= 120:
                raise ValueError('El intervalo de repetición debe estar entre 1 y 120 s de partida.')
            for name in ('visual_escala','idle_total_escala','edades_escala','controles_escala'):
                if not 50 <= int(self.config[name]) <= 180:
                    raise ValueError(f'La escala de {name} debe estar entre 50 y 180 %.')
            if not 80 <= int(self.config['visual_tamano']) <= 480:
                raise ValueError('El icono debe medir entre 80 y 480 px antes de aplicar la escala.')
            if not 0 <= self.config['visual_permanencia'] <= 30:
                raise ValueError('La permanencia visual debe estar entre 0 y 30 segundos.')
            if not 1 <= self.config['filtro_parpadeo_segundos'] <= 3:
                raise ValueError('La confirmación de producción debe ser de 1 a 3 s de partida.')
            if not 0.3 <= self.config['ocr_intervalo'] <= 1.5:
                raise ValueError('El intervalo OCR debe estar entre 0,3 y 1,5 s.')
            if self.config['canal_aviso'] not in ('visual', 'sonoro', 'ambos'):
                raise ValueError('Modo de aviso no válido.')
            if self.config['imagen_visual']:
                with Image.open(self.config['imagen_visual']) as img:
                    img.verify()
            if self.config['limite_minutos'] <= 0 or self.config['limite_aldeanos'] < 1:
                raise ValueError('Los límites deben ser positivos.')
            self.save()
            self.live_repeat_seconds = self.config['repeticion']
            if self.running_settings is not None:
                self.running_settings.update(self.config)
                # Redibuja solo ventanas visibles, sin obligar a reiniciar la partida.
                if self.visual_alert._visible:
                    options = (self.celebration_settings(self.running_settings)
                               if self.celebration_job is not None else self.running_settings)
                    self.visual_alert.show(options)
                if self.idle_total_on_var.get():
                    self.total_idle_overlay.show_total(self.running_settings)
                else:
                    self.total_idle_overlay.hide()
                if self.age_overlay_on_var.get():
                    self.age_idle_overlay.show_ages(self.running_settings)
                else:
                    self.age_idle_overlay.hide()
                if self.game_controls._visible:
                    self.game_controls.show_controls(self.running_settings)
            self.sync_visibility_buttons()
            if not self.visual_enabled_var.get():
                self.visual_alert.hide()
            if not self.idle_total_on_var.get():
                self.total_idle_overlay.hide()
            if not self.age_overlay_on_var.get():
                self.age_idle_overlay.hide()
            self.log('Preferencias guardadas (incluido reconocimiento de tecnologías y visibilidad). Repetición de sonido: '+str(self.config['repeticion'])+' s de partida.')
        except Exception as exc:
            messagebox.showerror('Configuración', str(exc))

    def log(self, message):
        self.msg_queue.put(('log', message))

    def refresh_calib_label(self):
        zones = self.config.get('zonas', [])
        self.calib_label.config(text=f'{len(zones)} zona(s) guardada(s). Plantilla: '+
                                (str(len(load_templates()))+' modelos disponibles')+
                                ' | Reloj: '+('SÍ' if self.config.get('zona_tiempo') else 'NO')+
                                ' | Aldeanos: '+('SÍ' if self.config.get('zona_aldeanos') else 'NO') +
                                ' | Pausa: '+('SÍ' if self.config.get('zona_pausa') and PAUSE_TEMPLATE.exists() and RUNNING_TEMPLATE.exists() else 'NO')+
                                ' | Escudo: '+('SÍ' if self.config.get('zona_edad') else 'NO')+
                                ' | Texto edad: '+('SÍ' if self.config.get('zona_edad_texto') else 'NO')+
                                ' | Rojo: '+('SÍ' if self.config.get('zona_rojo') else 'NO'))

    @staticmethod
    def _validate_zone_data(data):
        if not isinstance(data.get('zonas', []), list):
            raise ValueError('Lista de zonas no válida.')
        def check_rect(rect):
            if not isinstance(rect, (list, tuple)) or len(rect) != 4:
                raise ValueError('Rectángulo de zona no válido.')
            if any(not isinstance(v, int) or isinstance(v, bool) for v in rect):
                raise ValueError('Coordenadas de zona no numéricas.')
            x, y, w, h = rect
            if x < 0 or y < 0 or w < 2 or h < 2 or max(rect) > 100000:
                raise ValueError('Coordenadas de zona fuera de rango.')
        for z in data.get('zonas', []):
            if not isinstance(z, dict) or not isinstance(z.get('nombre'), str):
                raise ValueError('Nombre de zona no válido.')
            check_rect(z.get('rect'))
        for name in ('zona_tiempo', 'zona_aldeanos', 'zona_pausa', 'zona_edad', 'zona_edad_texto', 'zona_rojo'):
            if data.get(name) is not None:
                check_rect(data[name])
        mon = data.get('monitor', 1)
        if not isinstance(mon, int) or not 1 <= mon <= 64:
            raise ValueError('Número de monitor no válido.')
        if data.get('modo', 'global') not in ('global', 'individual'):
            raise ValueError('Modo de detección no válido.')

    def save(self):
        # Escritura atómica: evita perder la configuración ante un cierre inesperado.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.config, ensure_ascii=False, indent=2)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                 dir=str(DATA_DIR), suffix='.tmp', delete=False) as temp:
            temp.write(payload)
            temporary = Path(temp.name)
        try:
            temporary.replace(CFG_FILE)
        finally:
            temporary.unlink(missing_ok=True)

    def export_zones(self):
        if not self.config.get('zonas'):
            messagebox.showwarning('Zonas', 'Calibra al menos una zona antes de exportar.')
            return
        target = filedialog.asksaveasfilename(parent=self.root,
            defaultextension='.json', initialfile='zonas_aoe2.json',
            filetypes=[('Configuración de zonas', '*.json')])
        if not target:
            return
        profile = {'version': 26, 'version_detector_edad': 26}
        profile.update({k: copy.deepcopy(self.config.get(k)) for k in ZONE_KEYS})
        # Las imágenes de la pausa se guardan aparte en LOCALAPPDATA.
        # Recalibra la pausa al cambiar de equipo o diseño del HUD.
        Path(target).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
        self.log('Copia de zonas exportada: '+target)

    def import_zones(self):
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Zonas', 'Detén antes de importar una calibración.')
            return
        source = filedialog.askopenfilename(parent=self.root,
            filetypes=[('Configuración de zonas', '*.json')])
        if not source:
            return
        try:
            incoming = json.loads(Path(source).read_text(encoding='utf-8'))
            if not isinstance(incoming, dict):
                raise ValueError('El archivo no contiene una configuración.')
            old_ages = incoming.get('version_detector_edad', incoming.get('version', 0)) < 22
            incoming = {k: copy.deepcopy(incoming[k]) for k in ZONE_KEYS if k in incoming}
            if old_ages:
                incoming.pop('zona_edad', None)
            proposed = {**self.config, **incoming}
            self._validate_zone_data(proposed)
            self.config.update(incoming)
            self.mode_var.set(self.config['modo'])
            self.monitor_var.set(str(self.config['monitor']))
            self.save()
            self.refresh_calib_label()
            self.log('Zonas importadas y guardadas: '+source)
            messagebox.showinfo('Zonas', 'Calibración recuperada. Escudo y texto se guardan de forma independiente; calibra la fuente que falte.')
        except Exception as exc:
            messagebox.showerror('Importar zonas', str(exc))

    def monitor_id(self):
        monitor = int(self.monitor_var.get())
        with mss.mss() as sct:
            if not 1 <= monitor < len(sct.monitors):
                raise ValueError(f'Número de monitor no válido. Disponibles: 1 a {len(sct.monitors)-1}')
        return monitor

    def calibrate(self):
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Calibración', 'Detén la monitorización antes de calibrar.')
            return
        try:
            monitor = self.monitor_id()
            mode = self.mode_var.get()
            messagebox.showinfo('Calibración',
                'Coloca AoE2 DE con un aldeano en producción visible en la cola global.\n\n'
                'Tras aceptar, dispones de 4 segundos para volver al juego.\n'
                'En la imagen capturada, selecciona el rectángulo con ENTER.')
            self.root.withdraw()
            try:
                time.sleep(4)
                with mss.mss() as sct:
                    image = grab_monitor(sct, monitor)
                # Plantilla independiente del ROI, destinada al icono solamente.
                trect = choose_rect('1 - Selecciona SOLO interior del icono de aldeano', image)
                x, y, w, h = trect
                template = image[y:y+h, x:x+w]
                if cv2.cvtColor(template, cv2.COLOR_BGR2GRAY).std() < 7:
                    raise ValueError('Icono demasiado uniforme; selecciona la imagen del aldeano sin borde.')
                zones = []
                if mode == 'global':
                    area = choose_rect('2 - Selecciona TODA la cola global', image)
                    zones.append({'nombre': 'Cola global', 'rect': area})
                else:
                    # Pedir cantidad exacta antes de capturar zonas independientes.
                    from tkinter import simpledialog
                    # Dialogo temporal: mostrar antes de capturar para mantener interfaz accesible.
                    self.root.deiconify()
                    count = simpledialog.askinteger('Centros urbanos',
                        'Número de indicadores independientes que se ven simultáneamente (1–12):',
                        minvalue=1, maxvalue=12, parent=self.root)
                    self.root.withdraw()
                    if count is None:
                        raise ValueError('Calibración cancelada.')
                    for i in range(count):
                        rect = choose_rect(f'2 - Indicador de producción del TC {i+1} ({i+1}/{count})', image)
                        zones.append({'nombre': f'TC {i+1}', 'rect': rect})
                # Selección opcional de zonas numéricas del HUD para límites.
                # Deben contener únicamente los dígitos, sin iconos ni texto adicional.
                from tkinter import messagebox as mb
                self.root.deiconify()
                wants_clock = mb.askyesno('Reloj',
                    '¿Quieres seleccionar el reloj de la partida? Es necesario para mostrar tiempo sin producir y aldeanos perdidos, así como para el límite por minuto.')
                self.root.withdraw()
                clock_rect = choose_rect('3 - SOLO dígitos del reloj (HH:MM:SS)', image) if wants_clock else self.config.get('zona_tiempo')
                self.root.deiconify()
                wants_pop = mb.askyesno('Aldeanos',
                    '¿Quieres seleccionar el número de aldeanos (solo el número junto al icono azul)?')
                self.root.withdraw()
                pop_rect = choose_rect('4 - SOLO número de aldeanos', image) if wants_pop else self.config.get('zona_aldeanos')
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(TEMPLATE_FILE), template)
                models = load_templates()
                scores = [match_score(image[r['rect'][1]:r['rect'][1]+r['rect'][3],
                                             r['rect'][0]:r['rect'][0]+r['rect'][2]],
                                      models, [1.0])[0] for r in zones]
                self.config.update({'modo': mode, 'modo_calibrado': mode, 'monitor': monitor, 'zonas': zones,
                                    'zona_tiempo': clock_rect, 'zona_aldeanos': pop_rect})
                self.save()
                self.refresh_calib_label()
                self.log('Calibración lista. Similitud inicial por zona: ' +
                         ', '.join(f'{z["nombre"]}={s:.2f}' for z, s in zip(zones, scores)))
                if any(s < float(self.threshold_var.get()) for s in scores):
                    messagebox.showwarning('Verificación',
                        'Alguna zona obtuvo poca similitud. Revisa la calibración: '\
                        'en el modo individual cada zona debe corresponder a un TC DISTINTO.')
            finally:
                cv2.destroyAllWindows()
                self.root.deiconify()
                self.root.lift()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Calibración', str(exc))

    def calibrate_red(self):
        """Marca SOLO el icono cuando aparezca rojo. No hace falta OCR.

        La zona se guarda como coordenadas de pantalla del monitor de captura.
        """
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Rojo','Detén la monitorización antes de calibrar.')
            return
        try:
            monitor=self.monitor_id()
            messagebox.showinfo('Calibrar icono ROJO',
                'Deja un icono de aldeano en estado ROJO visible en el juego.\n'
                'Después de aceptar, tendrás 4 segundos para volver a AoE2.\n'
                'Selecciona solamente el interior de ese icono ROJO y pulsa ENTER.')
            self.root.withdraw()
            try:
                time.sleep(4)
                with mss.mss() as sct:
                    frame=grab_monitor(sct,monitor)
                rect=choose_rect('ICONO ROJO - ENTER',frame)
                x,y,w,h=rect
                ratio=red_coverage(frame[y:y+h,x:x+w])
                if ratio < .04:
                    raise ValueError(f'El recorte solo tiene {ratio*100:.1f}% de rojo; debe verse '
                                     'el estado rojo al calibrar, sin el borde del HUD.')
                self.config.update({'zona_rojo':rect,'rojo_ratio_ref':round(ratio,4),
                                    'rojo_activo':True,'monitor':monitor})
                self.red_on_var.set(True)
                self.save()
                self.refresh_calib_label()
                self.log(f'Icono rojo calibrado: {ratio*100:.1f}% rojo, zona {rect}')
            finally:
                cv2.destroyAllWindows()
                self.root.deiconify()
                self.root.lift()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Calibrar rojo',str(exc))

    def calibrate_pause(self):
        """Calibración visual independiente de la tecla de pausa del jugador."""
        if self.thread and self.thread.is_alive():
            messagebox.showwarning('Pausa', 'Detén la monitorización antes de calibrar.')
            return
        try:
            monitor=self.monitor_id()
            messagebox.showinfo('Calibrar pausa',
                'En el juego, puedes usar CUALQUIER tecla/botón para PAUSAR.\n\n'
                'Al aceptar tendrás 5 segundos para pausar. Se captura la pantalla '
                'y después seleccionarás SOLO el cartel o símbolo de PAUSA.')
            self.root.withdraw()
            try:
                paused_image=capture_after_pause_button(monitor,5)
                area=choose_rect('CARTEL PAUSA (ENTER para confirmar)',paused_image)
                self.root.deiconify()
                messagebox.showinfo('Reanudar partida',
                    'Al aceptar tendrás 5 segundos para REANUDAR con tu tecla o botón '
                    'habitual. Se guardará una referencia del juego sin pausa.')
                self.root.withdraw()
                running_image=capture_after_pause_button(monitor,5)
                x,y,w,h=area
                paused_part=paused_image[y:y+h,x:x+w]
                running_part=running_image[y:y+h,x:x+w]
                separation=float(np.mean(cv2.absdiff(
                    cv2.cvtColor(paused_part,cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(running_part,cv2.COLOR_BGR2GRAY))))
                if separation<8:
                    raise ValueError('El cartel calibrado no cambia suficiente entre pausa y juego. '
                                     'Selecciona la zona del indicador PAUSA, no la escena.')
                DATA_DIR.mkdir(parents=True,exist_ok=True)
                cv2.imwrite(str(PAUSE_TEMPLATE),paused_part)
                cv2.imwrite(str(RUNNING_TEMPLATE),running_part)
                self.config['zona_pausa']=area
                self.config['monitor']=monitor
                self.save()
                self.refresh_calib_label()
                self.log('Pausa calibrada para cualquier tecla o botón. Diferencia %.1f'%separation)
            finally:
                cv2.destroyAllWindows()
                self.root.deiconify()
                self.root.lift()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Calibración de pausa',str(exc))

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        if self.preview_controls_active:
            self.preview_controls_active=False
            self.visual_alert.hide()
            self.total_idle_overlay.hide()
            self.age_idle_overlay.hide()
        try:
            self.idle_goals()
            selected_mode = self.mode_var.get()
            if selected_mode != self.config.get('modo_calibrado', self.config.get('modo')):
                raise ValueError('Has cambiado el modo. Vuelve a calibrar.')
            self.save_preferences()
            self.config['modo'] = selected_mode
            self.config['monitor'] = self.monitor_id()
            self.config['umbral'] = float(self.threshold_var.get())
            self.config['espera'] = 3.0
            self.config['repeticion'] = float(self.repeat_var.get())
            self.config['solo_juego_activo'] = self.foreground_var.get()
            if not 0.35 <= self.config['umbral'] <= 0.90:
                raise ValueError('El umbral debe estar entre 0.35 y 0.90.')
            if not self.config['zonas'] or not load_templates():
                raise ValueError('Primero pulsa «Calibrar pantalla».')
            if len(self.config['zonas']) > 1 and self.config['modo'] != 'individual':
                raise ValueError('Recalibra el modo global.')
            for kind, enabled, zone in [('tiempo', self.config['limite_tiempo_activo'], self.config.get('zona_tiempo')),
                                        ('aldeanos', self.config['limite_aldeanos_activo'], self.config.get('zona_aldeanos'))]:
                if enabled and not zone:
                    raise ValueError(f'Has activado el límite de {kind}, pero no has calibrado su zona.')
            if (self.config['limite_tiempo_activo'] or self.config['limite_aldeanos_activo']) and not find_tesseract():
                raise ValueError('Para leer reloj/aldeanos debes instalar Tesseract OCR. Consulta LEEME.txt.')
            if self.config['canal_aviso'] != 'visual' and self.config['sonido'] == 'archivo' and not Path(self.config['archivo_sonido']).is_file():
                raise ValueError('No se encuentra el archivo MP3/WAV seleccionado.')
            if not self.config.get('zona_tiempo') or not find_tesseract():
                raise ValueError('V21: todos los contadores IDLE usan el reloj de la partida. Calibra el reloj e instala Tesseract OCR.')
            if self.config.get('edades_visible',False) and not (self.config.get('zona_edad') or self.config.get('zona_edad_texto')):
                raise ValueError('Para mostrar IDLE por edades, calibra el escudo y/o el texto de edad.')
            if self.config.get('edades_visible',False) and self.config.get('zona_edad') and len(load_age_signatures()) != 4:
                raise ValueError('Faltan las cuatro imágenes de las edades.')
            if self.config.get('idle_total_visible', False) and (not self.config.get('zona_tiempo') or not find_tesseract()):
                raise ValueError('El IDLE TC acumulado requiere zona del reloj calibrada y Tesseract OCR.')
            if self.config.get('reiniciar_al_reloj_cero', True) and (not self.config.get('zona_tiempo') or not find_tesseract()):
                self.log('Reinicio automático no disponible: calibra la zona del reloj e instala Tesseract OCR.')
            self.save()
        except Exception as exc:
            messagebox.showerror('Parámetros', str(exc))
            return
        self.finish_celebration()
        self.sound_engine.stop_sound(include_celebration=True)
        self.latest_visual_snapshot = None
        self.last_age_snapshot = None
        self.imperial_checked = False
        self.visual_alert.hide()
        self.total_idle_overlay.hide()
        self.total_idle_overlay.update_total(0)
        self.idle_total_text_var.set('00:00')
        self.latest_metrics = None
        self.reset_total_event.clear()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.worker, args=(self.config.copy(),), daemon=True)
        self.running_settings = self.config.copy()
        if self.config.get('idle_total_visible', False):
            self.total_idle_overlay.show_total(self.config)
        if self.config.get('edades_visible', False):
            self.age_idle_overlay.show_ages(self.config)
        if self.config.get('controles_visible',True):
            self.game_controls.show_controls(self.config)
            self.sync_visibility_buttons()
        self.thread.start()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_var.set('MONITORIZANDO')
        self.log('V26: OCR reloj mejorado y doble fuente de edad. Tecnologías TC reconocidas ('+str(len(load_technology_templates()))+' modelos), único reloj de partida. OCR cada '+str(self.config['ocr_intervalo'])+' s.')

    def worker(self, config):
        templates = load_templates()
        fishing_models = load_fishing_ship_models(config['escalas'])
        technology_templates = load_technology_templates() if config.get('tecnologias_activo',True) else []
        if not templates:
            self.msg_queue.put(('error', 'No se pudieron cargar los modelos.'))
            self.msg_queue.put(('stopped', None))
            return
        if config.get('tecnologias_activo',True) and not technology_templates:
            self.log('No hay modelos de tecnologías; se usará solo detección de aldeanos.')
        engine = ClockSynchronizedIdleFiltered(config.get('segundos_aldeano',25),
                                             config.get('filtro_parpadeo_segundos',1))
        age_engine = AgeIdleTracker()
        age_templates = load_age_signatures() if config.get('zona_edad') else {}
        age_text_enabled = bool(config.get('zona_edad_texto'))
        last_age_saved_clock = None
        last_age_saved_name = None
        latest_age_shot = None
        observed_age = None
        current_age_score = 0.0
        last_age_scan = -1e9
        age_detection_source = 'SIN LECTURA'
        restart_detector = MatchClockResetDetector()
        last_ocr, last_population = -1e9, -1e9
        last_log, last_alarm_clock = -1e9, None
        last_paused = None
        last_state = None
        hold_until = None
        held_metrics = None
        reached = False
        pop_val = None
        pop_confirm = 0
        prev_pop = None
        settings = config
        pause_region = config.get('zona_pausa')
        pause_ref = (cv2.imread(str(PAUSE_TEMPLATE), cv2.IMREAD_GRAYSCALE)
                     if PAUSE_TEMPLATE.exists() else None)
        run_ref = (cv2.imread(str(RUNNING_TEMPLATE), cv2.IMREAD_GRAYSCALE)
                   if RUNNING_TEMPLATE.exists() else None)
        try:
            with mss.mss() as sct:
                while not self.stop_event.is_set():
                    now = time.monotonic()  # SÓLO cadencia de CPU y mensajes, NUNCA IDLE.
                    if self.reset_total_event.is_set():
                        engine.reset_accumulated()
                        age_engine.reset()
                        last_age_saved_clock = None
                        last_age_saved_name = None
                        self.reset_total_event.clear()
                    if config['solo_juego_activo'] and not is_game_active():
                        engine.sample([], paused=True)
                        self.sound_engine.stop_sound()
                        self.msg_queue.put(('snapshot', {
                            'state':'PAUSADO', 'details':'AoE2 no está en primer plano.',
                            'metrics':None, 'visual_metrics':None, 'total':engine.total_seconds,
                            'hourglass_active':False,
                            'show_visual':False, 'ages':age_engine.snapshot()}))
                        self.stop_event.wait(.35)
                        continue
                    frame = grab_monitor(sct, config['monitor'])
                    paused_by_game = pause_image_is_active(frame, pause_region, pause_ref, run_ref)
                    paused_manually = self.manual_pause_event.is_set()
                    paused = paused_by_game or paused_manually
                    observations, scores, detected_kinds = [], [], []
                    for zone in config['zonas']:
                        x,y,w,h=zone['rect']
                        if min(x,y)<0 or x+w>frame.shape[1] or y+h>frame.shape[0]:
                            observations.append((zone['nombre'],None))
                            scores.append(-1.)
                            detected_kinds.append('fuera de pantalla')
                            continue
                        roi=frame[y:y+h,x:x+w]
                        producing, kind, confidence = classify_queue_region(
                            roi,templates,technology_templates,config['escalas'],
                            village_threshold=config['umbral'], fishing_models=fishing_models)
                        observations.append((zone['nombre'],bool(producing)))
                        scores.append(confidence)
                        detected_kinds.append(kind)
                    # El estado ROJO tiene prioridad incluso si la imagen del
                    # aldeano sigue presente. Solo se lee la ROI específica,
                    # nunca los marcos rojos ornamentales del HUD global.
                    red_zone=config.get('zona_rojo') if config.get('rojo_activo',True) else None
                    red_active=False
                    if red_zone:
                        rx,ry,rw,rh=red_zone
                        if min(rx,ry)>=0 and rx+rw<=frame.shape[1] and ry+rh<=frame.shape[0]:
                            # Un escudo/una tecnología puede incluir rojo natural.
                            # Exigimos VELO ROJO sobre el icono completo, no solo
                            # píxeles decorativos rojos (antiguo falso IDLE).
                            indicator = frame[ry:ry+rh,rx:rx+rw]
                            red_active = (red_overlay_on_icon(indicator) and
                                          not fishing_ship_boxes(indicator, fishing_models))
                        if red_active and observations:
                            # Asociar el rojo a su TC si comparte una zona.
                            matches=[i for i,z in enumerate(config['zonas']) if
                                     rect_overlap(z['rect'],red_zone) > 0]
                            if matches:
                                idx=matches[0]
                                if config['modo'] == 'individual':
                                    observations[idx]=(observations[idx][0],False)
                                # En cola global, un icono ROJO no anula otra
                                # producción activa detectada en la misma cola.
                            elif config['modo']=='global':
                                if not observations[0][1]:
                                    observations[0]=(observations[0][0],False)
                            else:
                                observations.append(('Indicador rojo',False))
                                scores.append(1.0)
                    clock_read = (now-last_ocr >= config.get('ocr_intervalo', .38))
                    read = None
                    if clock_read:
                        last_ocr = now
                        rect = config['zona_tiempo']
                        x,y,w,h=rect
                        if min(x,y)>=0 and x+w<=frame.shape[1] and y+h<=frame.shape[0]:
                            read=ocr_digits(frame[y:y+h,x:x+w], 'tiempo')
                        if read is not None and config.get('reiniciar_al_reloj_cero',True) and restart_detector.observe(read):
                            if latest_age_shot is not None:
                                store_age_snapshot(latest_age_shot,engine.current_clock,archive=True)
                            engine.reset()
                            age_engine.reset()
                            last_age_saved_clock=None
                            last_age_saved_name=None
                            observed_age=None
                            last_age_scan=-1e9
                            reached = False
                            pop_val = None
                            pop_confirm = 0
                            prev_pop = None
                            held_metrics = None
                            hold_until = None
                            last_alarm_clock = None
                            last_state = None
                            self.sound_engine.stop_sound()
                            self.msg_queue.put(('reset',
                                'Nueva partida: reloj '+format_game_duration(read)+'. Reinicio de IDLE y límites.'))
                        elif read is None and config.get('reiniciar_al_reloj_cero',True):
                            restart_detector.observe(None)
                    shot=engine.sample(observations, clock_read, read, paused=paused)
                    hourglass_active = (not paused and shot['clock_ok'] and
                                        (shot['idle'] > 0 or any(value is False for _, value in observations)))
                    # Dos fuentes independientes: escudo enmascarado + OCR de
                    # texto amarillo/blanco. Un desacuerdo no fuerza edad.
                    if ((age_templates or age_text_enabled) and
                            now-last_age_scan >= .6 and not paused):
                        last_age_scan = now
                        shield_age = None
                        text_age = None
                        if age_templates and config.get('zona_edad'):
                            ax,ay,aw,ah = config['zona_edad']
                            if min(ax,ay)>=0 and ax+aw<=frame.shape[1] and ay+ah<=frame.shape[0]:
                                shield_age,current_age_score = detect_game_age(
                                    frame[ay:ay+ah,ax:ax+aw], age_templates)
                        if age_text_enabled:
                            tx,ty,tw,th = config['zona_edad_texto']
                            if min(tx,ty)>=0 and tx+tw<=frame.shape[1] and ty+th<=frame.shape[0]:
                                text_age,_ = detect_game_age_text(
                                    frame[ty:ty+th,tx:tx+tw])
                        observed_age,age_detection_source = reconcile_age_observations(
                            shield_age, text_age)
                    ages=age_engine.observe(observed_age,shot['total'],
                                            clock_valid=shot['clock_ok'] and not paused)
                    latest_age_shot=ages
                    if ((age_templates or age_text_enabled) and shot['clock_ok'] and shot['clock'] is not None and
                            (last_age_saved_clock is None or ages['age']!=last_age_saved_name or
                             shot['clock']-last_age_saved_clock>=10)):
                        store_age_snapshot(ages,shot['clock'])
                        last_age_saved_clock=shot['clock']
                        last_age_saved_name=ages['age']
                    current_clock=shot['clock']
                    # Los límites siguen comprobándose incluso cuando ya se alcanzó uno.
                    if config['limite_aldeanos_activo'] and not reached and now-last_population>=1:
                        last_population=now
                        rect=config.get('zona_aldeanos')
                        if rect:
                            x,y,w,h=rect
                            if min(x,y)>=0 and x+w<=frame.shape[1] and y+h<=frame.shape[0]:
                                counted=ocr_digits(frame[y:y+h,x:x+w], 'aldeanos')
                                if counted is None:
                                    pop_confirm=0
                                else:
                                    pop_confirm = pop_confirm+1 if counted==prev_pop else 1
                                    prev_pop=counted
                                    pop_val=counted
                    if not reached and ((config['limite_tiempo_activo'] and shot['clock_ok'] and
                                       current_clock is not None and
                                       current_clock>=config['limite_minutos']*60) or
                                      (config['limite_aldeanos_activo'] and pop_val is not None and
                                       pop_confirm>=2 and pop_val>=config['limite_aldeanos'])):
                        reached=True
                        hold_until=None
                        held_metrics=None
                        self.sound_engine.stop_sound()
                    no_evidence=not observations or any(
                        v is None and name not in engine.confirmed
                        for name,v in observations)
                    if paused:
                        state='PAUSADO (AVISADOR)' if paused_manually else 'PAUSADO (JUEGO)'
                        hold_until=None
                        self.sound_engine.stop_sound()
                    elif reached:
                        state='LÍMITE ALCANZADO'
                    elif no_evidence:
                        state='INCIERTO'
                    elif not shot['clock_ok']:
                        state='RELOJ SIN LEER'
                    elif shot['idle']>=config['espera']:
                        state='ALERTA'
                    else:
                        state='NORMAL'
                    metrics=(shot['idle'],shot['lost']) if shot['clock_ok'] and not no_evidence else None
                    if state=='ALERTA':
                        held_metrics=metrics
                        hold_until=None
                    elif last_state=='ALERTA' and state=='NORMAL':
                        last_alarm_clock=None
                        # Mantener visualmente el último aviso DESPUÉS de reanudar
                        # la producción, según segundos DE JUEGO (no reloj Windows).
                        hold_until=(current_clock or 0)+config.get('visual_permanencia',2)
                        self.sound_engine.stop_sound()
                    elif state not in ('NORMAL','ALERTA'):
                        last_alarm_clock=None
                        hold_until=None
                        self.sound_engine.stop_sound()
                    show_visual = state=='ALERTA'
                    if state=='NORMAL' and hold_until is not None and current_clock is not None:
                        if current_clock < hold_until:
                            show_visual=True
                        else:
                            hold_until=None
                    if state=='ALERTA' and config['canal_aviso']!='visual' and not self.muted_event.is_set() and shot['clock_ok'] and current_clock is not None:
                        if audio_repeat_due(current_clock,last_alarm_clock,self.live_repeat_seconds):
                            self.sound_engine.play(config)
                            last_alarm_clock=current_clock
                    elif last_state=='ALERTA' and state!='ALERTA':
                        self.sound_engine.stop_sound()
                    detail=('IDLE '+format_game_duration(shot['idle'])+
                            ' · Acumulado '+format_game_duration(shot['total'])+
                            ' · Aldeanos no creados '+str(shot['lost']))
                    if shot.get('pendientes_produccion') and shot['clock_ok']:
                        detail += ' · Verificando producción (filtro antiparpadeo)'
                    if any(v is None for _,v in observations) and not no_evidence:
                        detail += ' · Lectura del icono incierta (IDLE conservado)'
                    if no_evidence:
                        detail='Zona no reconocida. Revisa la calibración de los iconos.'
                    if not shot['clock_ok'] and not paused:
                        detail='OCR del reloj no disponible; contador congelado.'
                    if paused:
                        detail='Pausa manual: IDLE congelado.' if paused_manually else 'Pausa del juego: IDLE congelado.'
                    if reached:
                        detail='Límite de partida alcanzado. Solo se vigila el reloj para reiniciar.'
                    # Snapshot ÚNICO: ambos HUD muestran cifras sincronizadas.
                    self.msg_queue.put(('snapshot', {
                        'state':state, 'details':detail, 'metrics':metrics,
                        'visual_metrics':held_metrics if show_visual else metrics,
                        'total':shot['total'], 'hourglass_active':hourglass_active,
                        'ages':ages, 'age_source':age_detection_source, 'show_visual':show_visual and
                        config['canal_aviso']!='sonoro' and not paused and not reached}))
                    if now-last_log>=2.5 or state!=last_state:
                        self.log('Estado '+state+' · '+detail+' · Edad '+
                                 AGE_NAMES.get(ages['age'],'sin detectar')+
                                 f' ({current_age_score:.2f}, {age_detection_source}) · '+
                            ' | '.join(f'{z[0]}={v:.2f} ({kind})' for z,v,kind in zip(observations,scores,detected_kinds)))
                        last_log=now
                    last_state=state
                    self.stop_event.wait(config['intervalo'])
        except Exception as exc:
            self.msg_queue.put(('error',str(exc)))
        finally:
            if latest_age_shot is not None and (age_templates or age_text_enabled):
                try:
                    store_age_snapshot(latest_age_shot,engine.current_clock)
                except Exception:
                    pass
            self.msg_queue.put(('stopped',None))

    def stop(self):
        self.finish_celebration()
        self.total_idle_overlay.update_total(self.total_idle_overlay.value_seconds,False)
        self.total_idle_overlay.hide()
        self.game_controls.hide()
        self.visual_alert.hide()
        self.sound_engine.stop_sound(include_celebration=True)
        self.latest_metrics = None
        self.stop_event.set()
        self.status_var.set('DETENIENDO…')

    def process_messages(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == 'log':
                    stamp = time.strftime('%H:%M:%S')
                    self.logbox.config(state='normal')
                    self.logbox.insert('end', f'{stamp}  {payload}\n')
                    if int(self.logbox.index('end-1c').split('.')[0]) > 170:
                        self.logbox.delete('1.0', '60.0')
                    self.logbox.see('end')
                    self.logbox.config(state='disabled')
                elif kind == 'snapshot':
                    self.latest_visual_snapshot = payload
                    self.status_var.set(payload['state'])
                    self.details_var.set(payload['details'])
                    self.latest_metrics = payload['metrics']
                    self.idle_total_text_var.set(format_game_duration(payload['total']))
                    self.total_idle_overlay.update_total(payload['total'],payload.get('hourglass_active',False))
                    if payload.get('ages'):
                        before = self.last_age_snapshot
                        self.last_age_snapshot=payload['ages']
                        self.age_idle_overlay.update_ages(payload['ages'])
                        age_name = AGE_NAMES.get(payload['ages'].get('age'), 'sin identificar')
                        self.current_age_var.set('Edad reconocida: '+age_name + ' · Fuente: ' + payload.get('age_source','--'))
                        previous_age = before.get('age') if before else None
                        current_age = payload['ages']['age']
                        if (self.running_settings is not None and not self.stop_event.is_set() and
                                previous_age in AGE_ORDER[:-1] and
                                current_age == AGE_ORDER[AGE_ORDER.index(previous_age) + 1]):
                            self.check_idle_goal(previous_age, payload['ages']['values'][previous_age])
                    if self.celebration_job is None:
                        self.render_visual_snapshot()
                elif kind == 'reset':
                    self.finish_celebration()
                    self.sound_engine.stop_sound(include_celebration=True)
                    self.latest_visual_snapshot = None
                    self.imperial_checked = False
                    self.latest_metrics = None
                    self.last_age_snapshot = None
                    self.idle_total_text_var.set('00:00')
                    self.total_idle_overlay.update_total(0,False)
                    self.age_idle_overlay.update_ages(AgeIdleTracker().snapshot())
                    self.visual_alert.hide()
                    self.visual_alert.update_metrics(None)
                    self.current_age_var.set('Nueva partida: esperando escudo/texto de edad')
                    self.status_var.set('NUEVA PARTIDA')
                    self.details_var.set(payload)
                    self.log(payload)
                elif kind == 'total_idle':
                    self.idle_total_text_var.set(format_game_duration(payload))
                    self.total_idle_overlay.update_total(payload)
                elif kind == 'metrics':
                    self.latest_metrics = payload
                    self.visual_alert.update_metrics(payload)
                elif kind == 'error':
                    self.visual_alert.hide()
                    self.logbox.config(state='normal')
                    self.logbox.insert('end', 'ERROR: '+payload+'\n')
                    self.logbox.config(state='disabled')
                elif kind == 'stopped':
                    self.finish_celebration()
                    self.latest_visual_snapshot = None
                    self.game_controls.hide()
                    self.total_idle_overlay.hide()
                    self.age_idle_overlay.hide()
                    self.visual_alert.hide()
                    self.running_settings = None
                    self.latest_metrics = None
                    self.start_button.config(state='normal')
                    self.stop_button.config(state='disabled')
                    self.status_var.set('DETENIDO')
        except queue.Empty:
            pass
        self.root.after(120, self.process_messages)

    def close(self):
        self.stop_event.set()
        self.finish_celebration()
        self.sound_engine.close()
        self.visual_alert.close()
        self.total_idle_overlay.close()
        self.age_idle_overlay.close()
        self.game_controls.close()
        self.root.destroy()


def main():
    set_dpi_awareness()
    root = tk.Tk()
    apply_parchment_theme(root)
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()

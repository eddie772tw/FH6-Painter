import os

class ColorHSV:

    def __init__(self, h: float, s: float, v: float, a: float=1.0):
        self.h = h
        self.s = s
        self.v = v
        self.a = a

class ColorRGBA:

    def __init__(self, r: int, g: int, b: int, a: int=255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

def hsv_to_rgb(hsv: ColorHSV) -> ColorRGBA:
    h_clamped = max(0.0, min(1.0, hsv.h))
    s_clamped = max(0.0, min(1.0, hsv.s))
    v_clamped = max(0.0, min(1.0, hsv.v))
    a_clamped = max(0.0, min(1.0, hsv.a))
    r, g, b = (0.0, 0.0, 0.0)
    if s_clamped == 0.0:
        r = g = b = v_clamped
    else:
        hue_fraction = h_clamped
        if hue_fraction >= 1.0:
            hue_fraction = 0.0
        sector = int(hue_fraction / 0.16666667)
        f = hue_fraction / 0.16666667 - float(sector)
        p = (1.0 - s_clamped) * v_clamped
        q = (1.0 - s_clamped * f) * v_clamped
        t = (1.0 - s_clamped * (1.0 - f)) * v_clamped
        if sector == 0:
            r, g, b = (v_clamped, t, p)
        elif sector == 1:
            r, g, b = (q, v_clamped, p)
        elif sector == 2:
            r, g, b = (p, v_clamped, t)
        elif sector == 3:
            r, g, b = (p, q, v_clamped)
        elif sector == 4:
            r, g, b = (t, p, v_clamped)
        elif sector == 5:
            r, g, b = (v_clamped, p, q)
    return ColorRGBA(int(max(0.0, min(255.0, r * 255.0 + 0.5))), int(max(0.0, min(255.0, g * 255.0 + 0.5))), int(max(0.0, min(255.0, b * 255.0 + 0.5))), int(max(0.0, min(255.0, a_clamped * 255.0 + 0.5))))

def trim(value: str) -> str:
    return value.strip()

def replace_setting(text: str, key: str, value: str) -> str:
    lines = text.replace('\r\n', '\n').split('\n')
    replaced = False
    for i in range(len(lines)):
        if lines[i].lower().startswith(key.lower() + ' ='):
            lines[i] = f'{key} = {value}'
            replaced = True
            break
    if not replaced:
        if len(lines) > 0 and len(lines[-1]) == 0:
            lines[-1] = f'{key} = {value}'
        else:
            lines.append(f'{key} = {value}')
    return '\n'.join(lines)

def build_save_at(layer_count: int) -> str:
    values = []
    for n in range(500, layer_count, 500):
        values.append(n)
    if layer_count not in values:
        values.append(layer_count)
    return ','.join((str(x) for x in values))

def update_profiles_for_layer_count(root_dir: str, layer_count: int) -> None:
    settings_dir = os.path.join(root_dir, 'settings')
    if not os.path.isdir(settings_dir):
        return
    save_at = build_save_at(layer_count)
    updated_files = 0
    for filename in os.listdir(settings_dir):
        if filename.lower().endswith('.ini'):
            filepath = os.path.join(settings_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = replace_setting(content, 'saveAt', save_at)
                content = replace_setting(content, 'stopAt', str(layer_count))
                with open(filepath, 'w', encoding='utf-8', newline='\r\n') as f:
                    f.write(content)
                updated_files += 1
            except Exception as e:
                print(f'[Warning] Failed to update config {filename}: {e}')
    print(f'Updated {updated_files} generator profiles: stopAt={layer_count}, saveAt={save_at}')
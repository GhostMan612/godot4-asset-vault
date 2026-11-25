shader_type canvas_item;

uniform float cell_size = 64.0;
uniform float line_thickness = 1.5;
uniform vec4 line_color : source_color = vec4(0.0, 0.898, 1.0, 0.18);
uniform vec2 grid_offset = vec2(0.0, 0.0);

void fragment() {
    vec2 pos = (UV / TEXTURE_PIXEL_SIZE) + grid_offset;
    vec2 cell = mod(pos, cell_size);
    float lx = step(cell.x, line_thickness);
    float ly = step(cell.y, line_thickness);
    float mask = clamp(lx + ly, 0.0, 1.0);
    COLOR = vec4(line_color.rgb, line_color.a * mask);
}

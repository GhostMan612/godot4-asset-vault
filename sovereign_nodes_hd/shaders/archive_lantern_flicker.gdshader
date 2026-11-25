shader_type canvas_item;
render_mode blend_add;

uniform vec4 glow_color : source_color = vec4(0.30, 0.88, 0.95, 0.35);
uniform float flicker_speed = 6.5;
uniform float flicker_amp : hint_range(0.0, 0.3) = 0.08;

void fragment() {
    float dist = distance(UV, vec2(0.5)) * 2.0;
    float pulse = 1.0 + sin(TIME * flicker_speed) * flicker_amp + cos(TIME * flicker_speed * 2.3) * (flicker_amp * 0.5);
    float falloff = clamp(1.0 - dist, 0.0, 1.0);
    falloff = falloff * falloff * pulse;
    COLOR = vec4(glow_color.rgb, glow_color.a * falloff);
}

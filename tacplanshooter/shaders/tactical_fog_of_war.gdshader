shader_type canvas_item;

uniform sampler2D noise_tex : repeat_enable;
uniform vec4 fog_color : source_color = vec4(0.05, 0.07, 0.10, 0.88);
uniform float scroll_speed = 0.02;
uniform float density : hint_range(0.0, 1.0) = 0.85;

void fragment() {
    vec2 uv1 = UV + vec2(TIME * scroll_speed, TIME * scroll_speed * 0.4);
    vec2 uv2 = UV - vec2(TIME * scroll_speed * 0.6, TIME * scroll_speed * 0.25);
    float n = (texture(noise_tex, uv1).r + texture(noise_tex, uv2).r) * 0.5;
    vec4 base = texture(TEXTURE, UV);
    float alpha = clamp(base.a * density * (0.75 + n * 0.35), 0.0, 1.0);
    COLOR = vec4(fog_color.rgb, alpha * fog_color.a);
}

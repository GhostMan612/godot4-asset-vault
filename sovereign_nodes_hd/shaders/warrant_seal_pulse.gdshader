shader_type canvas_item;

uniform vec4 seal_color : source_color = vec4(0.85, 0.14, 0.22, 1.0);
uniform float pulse_speed = 2.6;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float glow = (0.5 + 0.5 * sin(TIME * pulse_speed)) * 0.32;
    COLOR = vec4(tex.rgb + seal_color.rgb * glow * tex.a, tex.a);
}

shader_type canvas_item;
render_mode blend_add;

uniform vec4 light_color : source_color = vec4(0.75, 0.92, 1.0, 0.32);
uniform float cone_half_angle : hint_range(0.1, 1.2) = 0.46;
uniform float softness : hint_range(0.02, 0.5) = 0.18;

void fragment() {
    vec2 p = UV - vec2(0.0, 0.5);
    float dist = length(p);
    float ang = abs(atan(p.y, max(p.x, 0.0001)));
    float cone = 1.0 - smoothstep(cone_half_angle - softness, cone_half_angle, ang);
    float falloff = clamp(1.0 - dist, 0.0, 1.0);
    falloff = falloff * falloff;
    COLOR = vec4(light_color.rgb, light_color.a * cone * falloff);
}

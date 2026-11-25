shader_type canvas_item;

uniform vec4 ring_color : source_color = vec4(0.0, 0.898, 1.0, 1.0);
uniform float pulse_speed = 3.2;
uniform float ring_radius : hint_range(0.1, 0.48) = 0.38;
uniform float ring_width : hint_range(0.01, 0.15) = 0.06;

void fragment() {
    vec2 centered = UV - vec2(0.5);
    float dist = length(centered);
    float pulse = 0.5 + 0.5 * sin(TIME * pulse_speed);
    float r = ring_radius + pulse * 0.03;
    float edge = 1.0 - smoothstep(ring_width * 0.5, ring_width, abs(dist - r));
    COLOR = vec4(ring_color.rgb, edge * (0.65 + 0.35 * pulse));
}

shader_type canvas_item;

uniform float threshold : hint_range(0.4, 0.95) = 0.72;
uniform float glow_boost : hint_range(0.0, 2.0) = 0.65;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float peak = max(tex.r, max(tex.g, tex.b));
    float emissive = smoothstep(threshold, 1.0, peak);
    COLOR = vec4(tex.rgb + tex.rgb * emissive * glow_boost, tex.a);
}

#[vertex]

#version 450

#VERSION_DEFINES

layout(push_constant, std140) uniform Pos {
	vec4 src_rect;
	vec4 dst_rect;

	vec2 eye_center;
	float k1;
	float k2;

	float upscale;
	float aspect_ratio;
	uint layer;

	float hdr_white_point;
	uint hdr_enabled;
	uint hdr_debug_visualization;
}
data;

layout(location = 0) out vec2 uv;

void main() {
	vec2 base_arr[4] = vec2[](vec2(0.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 1.0), vec2(1.0, 0.0));
	uv = data.src_rect.xy + base_arr[gl_VertexIndex] * data.src_rect.zw;
	vec2 vtx = data.dst_rect.xy + base_arr[gl_VertexIndex] * data.dst_rect.zw;
	gl_Position = vec4(vtx * 2.0 - 1.0, 0.0, 1.0);
}

#[fragment]

#version 450

#VERSION_DEFINES

layout(push_constant, std140) uniform Pos {
	vec4 src_rect;
	vec4 dst_rect;

	vec2 eye_center;
	float k1;
	float k2;

	float upscale;
	float aspect_ratio;
	uint layer;

	float hdr_white_point;
	uint hdr_enabled;
	uint hdr_debug_visualization;
}
data;

layout(location = 0) in vec2 uv;

layout(location = 0) out vec4 color;

#ifdef USE_LAYER
layout(binding = 0) uniform sampler2DArray src_rt;
#else
layout(binding = 0) uniform sampler2D src_rt;
#endif

float apply_inverse_pq(float fd) {
	float y = fd / 10000.0;
	float m1 = 1305.0 / 8192.0;
	float m2 = 2523.0 / 32.0;
	float c1 = 107.0 / 128.0;
	float c2 = 2413.0 / 128.0;
	float c3 = 2392.0 / 128.0;

	return pow(((c1 + c2 * pow(y, m1)) / (1 + c3 * pow(y, m1))), m2);
}

float apply_pq(float e) {
	float m1 = 1305.0 / 8192.0;
	float m2 = 2523.0 / 32.0;
	float c1 = 107.0 / 128.0;
	float c2 = 2413.0 / 128.0;
	float c3 = 2392.0 / 128.0;

	return 10000.0 * pow((max(pow(e, 1.0 / m2) - c1, 0.0) / (c2 - c3 * pow(e, 1.0 / m2))), 1 / m1);
}

vec3 linear_to_pq(vec3 color) {
	const float color_to_nits_ratio = data.hdr_white_point;

	vec3 color_in_nits = color * color_to_nits_ratio;

	return vec3(
			apply_inverse_pq(color_in_nits.r),
			apply_inverse_pq(color_in_nits.g),
			apply_inverse_pq(color_in_nits.b));
}

vec3 pq_to_linear(vec3 color) {
	const float color_to_nits_ratio = data.hdr_white_point;

	vec3 color_in_nits = color * color_to_nits_ratio;

	return vec3(
			apply_pq(color_in_nits.r),
			apply_pq(color_in_nits.g),
			apply_pq(color_in_nits.b));
}

vec3 linear_to_srgb(vec3 color) {
	color = clamp(color, vec3(0.0), vec3(1.0));
	// Approximation from http://chilliant.blogspot.com/2012/08/srgb-approximations-for-hlsl.html
	return max(vec3(1.055) * pow(color, vec3(0.416666667)) - vec3(0.055), vec3(0.0));
}

// This expects 0-1 range input, outside that range it behaves poorly.
vec3 srgb_to_linear(vec3 color) {
	// Approximation from http://chilliant.blogspot.com/2012/08/srgb-approximations-for-hlsl.html
	return color * (color * (color * 0.305306011 + 0.682171111) + 0.012522878);
}

void main() {
#ifdef APPLY_LENS_DISTORTION
	vec2 coords = uv * 2.0 - 1.0;
	vec2 offset = coords - data.eye_center;

	// take aspect ratio into account
	offset.y /= data.aspect_ratio;

	// distort
	vec2 offset_sq = offset * offset;
	float radius_sq = offset_sq.x + offset_sq.y;
	float radius_s4 = radius_sq * radius_sq;
	float distortion_scale = 1.0 + (data.k1 * radius_sq) + (data.k2 * radius_s4);
	offset *= distortion_scale;

	// reapply aspect ratio
	offset.y *= data.aspect_ratio;

	// add our eye center back in
	coords = offset + data.eye_center;
	coords /= data.upscale;

	// and check our color
	if (coords.x < -1.0 || coords.y < -1.0 || coords.x > 1.0 || coords.y > 1.0) {
		color = vec4(0.0, 0.0, 0.0, 1.0);
	} else {
		// layer is always used here
		coords = (coords + vec2(1.0)) / vec2(2.0);
		color = texture(src_rt, vec3(coords, data.layer));
	}
#elif defined(USE_LAYER)
	color = texture(src_rt, vec3(uv, data.layer));
#else
	color = texture(src_rt, uv);
#endif

	if (data.hdr_enabled == 1) {
		vec3 linear_color = srgb_to_linear(color.rgb);

		if (data.hdr_debug_visualization == 1) {
			vec3 nits = linear_color * data.hdr_white_point;
			float average_nits = (nits.r + nits.g + nits.b) / 3.0;

			if (average_nits > 750) {
				linear_color.r = 0.0;
				linear_color.g = 0.0;
			} else if (average_nits > 500) {
				linear_color.r = 0.0;
				linear_color.b = 0.0;
			} else if (average_nits > 250) {
				linear_color.g = 0.0;
				linear_color.b = 0.0;
			}
		}

		vec3 pq_color = linear_to_pq(linear_color);

		color = vec4(pq_color.r, pq_color.g, pq_color.b, color.a);
	}
}

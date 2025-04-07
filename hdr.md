# HDR Notes
This is my experimental branch of Godot that adds in HDR output support. While it does somewhat work, there are important caveats to keep in mind:
- While it doesn't use anything Windows specific, this code has not been tested on any other platform.
- Enabling HDR output requires an app/editor restart. In practice that should not be needed, but I'm not familiar enough with how to reallocate buffers to do that.
- Currently there is no way to specify a working color space, so effectively all content is assumed to be in the extremely large Rec.2020 color space. Very few consumer monitors can even render this color space accurately, so this will likely make colors inaccurate.
- Only the ACES tonemapper is supported. Any other tonemapper will not work correctly.
- Glow seems to act a bit strange with HDR output enabled. I've had some success by increasing the HDR threshold to 2.
- My monitor is a basic model that only supports HDR10. I'm unsure if this code will work with HDR10+ or Dolby Vision.

## Known Issues
- You must turn on HDR support in the OS _before_ launching the editor. Otherwise, strange things will likely happen. On Windows, this means pressing `Win+Alt+B`. On macOS, this can be done by going to display settings. I'm not sure how to do it on Linux.
- Sometimes on my machine I get stuck in a sort of "quasi-HDR" mode after exiting the editor and switching out of HDR mode. If this happens, stay in SDR mode, relaunch the editor, and then immediately exit. If that fails, reboot.
- Some of the calculations in `tonemap.glsl` are inefficient and probably not optimal. Part of the problem is I'm not that familiar with how the ACES tonemapper works.
- I don't have much knowledge of how the Godot 4 renderer works, so I mostled just hacked in changes wherever they seemed to work. Most likely a "real" implementation would change things in other places and/or add new renderer steps.

## Settings
- "HDR Output Enabled": Turns HDR output on and off. Requires editor restart.
- "HDR White Point": Sets the paperwhite value in candelas per square meter. 250 is a good typical value. Also affects the UI.
- "HDR Peak Luminance Nits": Sets the value the tonemapper will consider the top end of the luminance curve, basically the point where the tonemapper will turn the object completely white to maximize brightness. I'd generally recommend setting this to your monitor's peak luminance plus about 100. Monitors usually list their peak brightness in their specs and/or certifications, and also on Windows 11 there's a calibration tool that will tell you this. There are OS APIs that allow querying this, so a final implementation might do that instead of letting the user set it.
- "Tone Mapper Exposure Modifier": Modifies the brightness of the 3D scene without affecting the UI. This is mainly to adjust the UI/scene brightness balance.
- "Debug Visualization": Adds a false-color visualization to the scene. If an object is below 250 nits, it renders normally. 250-500 nits is rendered in red, 500-750 is in green, and 750-1000 is in blue.

## Troubleshooting
- After launching, the Godot editor just looks really gray and washed out, and doesn't look any brighter: The code failed to find a HDR10 color mode. Either your monitor or driver setup doesn't support HDR10, or more likely it's using a color space I wasn't expecting.

## PQ / sRGB Functions
```c
float apply_inverse_pq(float fd){
	float y = fd / 10000.0;
	float m1 = 1305.0 / 8192.0;
	float m2 = 2523.0 / 32.0;
	float c1 = 107.0 / 128.0;
	float c2 = 2413.0 / 128.0;
	float c3 = 2392.0 / 128.0;

	return pow(((c1 + c2 * pow(y, m1)) / (1 + c3 * pow(y, m1))), m2);
}

float apply_pq(float e){
	float m1 = 1305.0 / 8192.0;
	float m2 = 2523.0 / 32.0;
	float c1 = 107.0 / 128.0;
	float c2 = 2413.0 / 128.0;
	float c3 = 2392.0 / 128.0;

	return 10000.0 * pow((max(pow(e, 1.0 / m2) - c1, 0.0) / (c2 - c3 * pow(e, 1.0 / m2))), 1 / m1);
}

vec3 linear_to_pq(vec3 color) {
	const float color_to_nits_ratio = 300;

	vec3 color_in_nits = color * color_to_nits_ratio;

	return vec3(
		apply_inverse_pq(color_in_nits.r),
		apply_inverse_pq(color_in_nits.g),
		apply_inverse_pq(color_in_nits.b)
	);
}

vec3 pq_to_linear(vec3 color) {
    const float color_to_nits_ratio = 300;

	vec3 color_in_nits = color * color_to_nits_ratio;

	return vec3(
		apply_pq(color_in_nits.r),
		apply_pq(color_in_nits.g),
		apply_pq(color_in_nits.b)
	);
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
```
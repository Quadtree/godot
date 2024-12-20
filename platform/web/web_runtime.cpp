/**************************************************************************/
/*  web_runtime.cpp                                                       */
/**************************************************************************/
/*                         This file is part of:                          */
/*                             GODOT ENGINE                               */
/*                        https://godotengine.org                         */
/**************************************************************************/
/* Copyright (c) 2014-present Godot Engine contributors (see AUTHORS.md). */
/* Copyright (c) 2007-2014 Juan Linietsky, Ariel Manzur.                  */
/*                                                                        */
/* Permission is hereby granted, free of charge, to any person obtaining  */
/* a copy of this software and associated documentation files (the        */
/* "Software"), to deal in the Software without restriction, including    */
/* without limitation the rights to use, copy, modify, merge, publish,    */
/* distribute, sublicense, and/or sell copies of the Software, and to     */
/* permit persons to whom the Software is furnished to do so, subject to  */
/* the following conditions:                                              */
/*                                                                        */
/* The above copyright notice and this permission notice shall be         */
/* included in all copies or substantial portions of the Software.        */
/*                                                                        */
/* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,        */
/* EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF     */
/* MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. */
/* IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY   */
/* CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,   */
/* TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE      */
/* SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                 */
/**************************************************************************/

#include <stdio.h>
#include <stdlib.h>

extern int godot_web_main(int argc, char *argv[]);

extern "C" {
void wasm_mono_entrypoint(int argc, void *argv) {
	printf("wasm_mono_entrypoint: That game engine you've been WAITING for has arrived!\n");

	printf("wasm_mono_entrypoint: argc=%d\n", argc);

	for (auto i = 0; i < argc; ++i) {
		char *argVal = ((char **)argv)[i];
		printf("wasm_mono_entrypoint: argv[%d]=%s\n", i, argVal);
	}

	auto returnCode = godot_web_main(argc, (char **)argv);
	printf("wasm_mono_entrypoint: Main function exited with code %d", returnCode);
}
}

int main(int argc, char *argv[]) {
	printf("That game engine you've been WAITING for has arrived!\n");
	return godot_web_main(argc, argv);
}

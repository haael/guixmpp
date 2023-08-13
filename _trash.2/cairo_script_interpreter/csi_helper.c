
#include "pycairo.h"

cairo_t* get_context_ptr(PycairoContext *obj)
{
	return obj->ctx;
}

cairo_surface_t* get_surface_ptr(PycairoSurface *obj)
{
	return obj->surface;
}


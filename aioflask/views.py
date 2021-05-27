import asyncio
from inspect import getmembers, iscoroutinefunction
from flask import views as original_views, request
from greenletio import await_


class View(original_views.View):
    @classmethod
    def lookup_async_method(cls):
        methods = getmembers(cls, predicate=iscoroutinefunction)
        name, func = next((meth for meth in methods), (None, None))
        return name, bool(func)

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        async_method, return_coro = cls.lookup_async_method()

        # if any of the class methods are async, return_coro is True
        # and this view function have to be a coroutine
        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            
            if async_method == 'dispatch_request':
                return await_(self.dispatch_request(*args, **kwargs))
            return self.dispatch_request(*args, **kwargs)

        view = asyncio.coroutine(view) if return_coro else view

        if cls.decorators:
            view.__name__ = name
            view.__module__ = cls.__module__
            for decorator in cls.decorators:
                view = decorator(view)

        view.view_class = cls
        view.__name__ = name
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.methods = cls.methods
        view.provide_automatic_options = cls.provide_automatic_options
        return view


class MethodView(View, metaclass=original_views.MethodViewType):
    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)

        if meth is None and request.method == "HEAD":
            meth = getattr(self, "get", None)

        assert meth is not None, f"Unimplemented method {request.method!r}"
        if iscoroutinefunction(meth):
            return await_(meth(*args, **kwargs))
        return meth(*args, **kwargs)

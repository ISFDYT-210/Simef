from django.shortcuts import redirect

class FirstLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs permitidas sin verificación
        allowed_paths = [
            '/accounts/login/',
            '/accounts/logout/',
            '/change_password_first/',
            '/change_password_first/done/',
            '/static/',
            '/media/',
            '/admin/',
        ]
        
        # CRÍTICO: Evitar el loop infinito
        if any(request.path.startswith(path) for path in allowed_paths):
            response = self.get_response(request)
            return response
        
        # Solo verificar si el usuario está autenticado y necesita cambiar contraseña
        if (request.user.is_authenticated and 
            hasattr(request.user, 'first_login') and 
            request.user.first_login and 
            not request.user.is_superuser and 
            not request.user.is_staff):
            
            return redirect('/change_password_first/')
        
        response = self.get_response(request)
        return response
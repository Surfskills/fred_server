# from django.http import JsonResponse
# from rest_framework_simplejwt.tokens import AccessToken
# from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
# from django.conf import settings
# import jwt

# class TokenAuthenticationMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if 'api/auth/signin' in request.path or 'api/auth/signup' in request.path:
#             return self.get_response(request)

#         auth_header = request.headers.get('Authorization', '')
#         if not auth_header.startswith('Bearer '):
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'Authentication token is missing'
#             }, status=401)

#         token = auth_header.split(' ')[1]
#         try:
#             AccessToken(token)
#             return self.get_response(request)
#         except (InvalidToken, TokenError):
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'Invalid or expired token'
#             }, status=401)
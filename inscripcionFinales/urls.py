# from re import template
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from .views import *
from .views import CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView, CustomPasswordResetCompleteView



urlpatterns = [
    #Usuarios del sistema   
    path('', HomePageView.as_view(), name= 'inicio'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', CustomLogoutView.as_view(), name='logout'),
    path("accounts/", include("django.contrib.auth.urls")),
    path("recuperar_pass/",auth_views.PasswordResetView.as_view(template_name="registration/recuperar_pass.html"),name='Recuperar Contraseña'),
    path("password_reset_done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_send.html"), name='password_reset_done'),
    path("create_user/",login_required(registerView.as_view(template_name= 'registration/register.html')), name='register'),
    path("career/", login_required(carreraView.as_view(template_name= 'carrera.html')), name='carrera'),
    path("institut/", login_required(carreraView.as_view(template_name= 'instituto.html')), name='instituto'),
    path("show_profile/", login_required(profileviews.as_view(template_name= 'registration/profile.html')), name='profile'),
    path("change_password/", auth_views.PasswordChangeView.as_view(template_name = 'registration/change_password.html'),name = 'cambiar_contraseña'),
    path("change_password_done/",auth_views.PasswordChangeDoneView.as_view(template_name='registration/success_password.html'), name='password_change_done'),
    path("user_list/",login_required(listUser.as_view(template_name='registration/list_user.html')),name='list_user'),
    path("edit_user/<int:pk>",login_required(editUser.as_view(template_name = 'registration/edit_profile.html')), name='edit_profile'),
    path("delete_user/<int:pk>",login_required(deleteUser.as_view(template_name='registration/delete_user.html')),name='delete_user'),
    path('eliminar_usuarios_seleccionados/', eliminar_usuarios, name='eliminar_usuarios_seleccionados'),
    path('eliminar_usuarios_seleccionados/', eliminar_usuarios, name='eliminar_usuarios_seleccionados'),
    path("show_user/<int:pk>",login_required(editUser.as_view(template_name = 'registration/show_user.html')), name='show_user'),
    path('password_reset/',auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html',email_template_name='registration/password_reset_email.html',success_url='/password_reset/done/'),name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reporte/<int:usuario_id>', reporte_estudiante_descarga, name='reporte_estudiante'),

    #Alta e Inscripcion materias
    
    path('altaMateria/', login_required(alta_materia), name='altaMateria'),
    path('exito-alta-materia/', login_required(exito_alta_materia), name='exito_alta_materia'),
    path('inscripcionMateriaEst/', login_required(lista_materias_user), name='listaMateriasUser'),
    path('listaMateriasEst/', login_required(lista_materias_inscriptas_user), name='lista_materias_inscriptas_user'),
    path('listaMateriasAdm/', login_required(lista_materias_inscriptas_adm), name='lista_materias_inscriptas_adm'),
    path('inscribirse_materia/<int:materia_id>/<int:modalidad>', inscripcionMateriaEst, name='inscribirse_materia'),
    path('inscripcionMateria/',inscripcionMateria, name='inscripcionMateria'),
    path('alta_masiva_materia/', login_required(alta_masiva_materia), name= 'AltaMasivaMaterias'),
    path('editar_materia/<int:id>/', login_required(editar_materia), name='editar_materia'),
    path('exito_cambios_materia/', login_required(exito_cambios_materia), name='exito_cambios_materia'),
    path('alerta_materia_existente', login_required(alerta_materia_existente), name='alerta_materia_existente'),
    path('ver_materias/<int:id>/', ver_materias, name='ver_materias'),
    path('abrir_inscripcion_materia/<int:carrera>/<int:anio>', abrir_inscripcion_materia, name='abrir_inscripcion_materia'),
    path('cerrar_inscripcion_materia/<int:carrera>/<int:anio>', cerrar_inscripcion_materia, name='cerrar_inscripcion_materia'),
    path('eliminar_materia/<int:id>/', login_required(eliminar_materia), name='eliminar_materia'),
    path('materias/eliminar_seleccionadas/', eliminar_materias_seleccionadas, name='eliminar_materias_seleccionadas'),
    path('eliminar_inscripcion_materia/<int:id>/', login_required(eliminar_inscripcion_materia), name='eliminar_inscripcion_materia'),
    path('exito_materia_eliminada/', exito_materia_eliminada, name='exito_materia_eliminada'),
    path('exito_materia_eliminada_est/', exito_materia_eliminada_est, name='exito_materia_eliminada_est'),
    path('exito_materia_eliminada_adm/', exito_materia_eliminada_adm, name='exito_materia_eliminada_adm'),
    path('lista_materias_admin/', lista_materias_admin, name='lista_materias_admin'),
    path('abrir_materias_seleccionadas/', abrir_materias_seleccionadas, name='abrir_materias_seleccionadas'),
    path('cerrar_materias_seleccionadas/', cerrar_materias_seleccionadas, name='cerrar_materias_seleccionadas'),
    path('abrir_mesas_seleccionadas/', abrir_mesas_seleccionadas, name='abrir_mesas_seleccionadas'),
    path('cerrar_mesas_seleccionadas/', cerrar_mesas_seleccionadas, name='cerrar_mesas_seleccionadas'),
    path('estudiantes/<int:usuario_id>/reporte_usuario_materias/', reporte_usuario_materias, name='reporte_usuario_materias'),
    path('reporte_html/<int:usuario_id>', reporte_estudiante_html, name='reporte_estudiante_html'),

    path('mesas_finales/cartel_pdf/', imprimir_mesas_finales_pdf, name='imprimir_mesas_finales_pdf'),

    #Alta e Inscripcion mesa de final Administrativo
    path('mesas_finales/', MesasFinalesListView.as_view(), name='mesas_finales_list'),
    path('inscribir_mesa_final/', inscribir_mesa_final, name='inscribir_mesa_final'),
    #Alta e Inscripcion mesa de final

    # Y AGREGAR solo estas dos nuevas rutas después de la línea 73:
    path('obtener_finales_estudiante/', obtener_finales_estudiante, name='obtener_finales_estudiante'),
    path('inscribir_final/', inscribir_final, name='inscribir_final'),

    path('acta_volante/<int:final_id>/', login_required(acta_volante), name='acta_volante'),
    path('exito_final_eliminado_est/', exito_final_eliminado_est, name='exito_final_eliminado_est'),
    path('exito_final_eliminado_adm/', exito_final_eliminado_adm, name='exito_final_eliminado_adm'),
    path('TESTINGlistamateriasfinal/',listarMateriasFinal,name='listarMesas'),
    path('eliminar_inscripcion_final/<int:id>/', login_required(eliminar_inscripcion_final), name='eliminar_inscripcion_final'),
    path('altaMesa/',altaMesa, name='altaMesa'),
    path("edit_mesa/<int:pk>", login_required(editMesa), name='edit_mesa'),
    path('listaFinalesEst/', login_required(lista_finales_inscriptos_user), name='lista_finales_inscriptos_user'),
    path('listaFinalesAdm/', login_required(lista_finales_inscriptos_adm), name='lista_finales_inscriptos_adm'),
    path('inscripcionMesa/',inscripcionMesa,name='inscripcionMesa'), 
    path('exito-inscripcion/', exito_inscripcion_final, name='exito_inscripcion_final'),
    path('exito_alta_mesa/', exito_alta_mesa, name='exito_alta_mesa'),
    path('inscripcionFinal/',inscripcionFinal, name='inscripcionFinal'),
    path("edit_inscr/<int:pk>",login_required(editInscr.as_view(template_name = 'registration/edit_inscr.html')), name='edit_inscr'),
    path('cargar_nota_final/<int:inscripcion_id>/',cargar_nota_final, name='cargar_nota_final'),
    path('cargar_nota_cursada/<int:id>/',editar_notas, name='cargar_nota_cursada'),
    path('exito_inscripcion_mesa/', exito_inscripcion_mesa, name='exito_inscripcion_mesa'),
    path('error_alta_mesa/', error_alta_mesa, name='error_alta_mesa'),
    path('error_inscripcion_adm/', error_inscripcion_adm, name='error_inscripcion_adm'),
    path('error_inscripcion_est/', error_inscripcion_est, name='error_inscripcion_est'),
    path('error_inscripcion_est1/', error_inscripcion_est1, name='error_inscripcion_est1'),
    path('error_inscripcion_est2/', error_inscripcion_est2, name='error_inscripcion_est2'),
    path('error_inscripcion_est3/', error_inscripcion_est3, name='error_inscripcion_est3'),
    path('error_inscripcion_est5/', error_inscripcion_est5, name='error_inscripcion_est5'),
    path('error_inscripcion_est6/', error_inscripcion_est6, name='error_inscripcion_est6'),
    path('inscripcionFinalEst/', login_required(lista_finales_user), name='listafinalesUser'),
    path("inscripcion_finales_lista/",login_required(listInscripcion.as_view(template_name='finales/list_inscripcion.html')),name='list_inscripcion'),
    path('inscribirse_final/<int:final_id>', inscripcionFinalEst, name='inscribirse_final'),
    path("mesas_lista/",login_required(listMesa.as_view(template_name='finales/list_mesa.html')),name='list_mesa'),
    path('mesas/eliminar_seleccionadas/', eliminar_mesas_seleccionadas, name='eliminar_mesas_seleccionadas'),
    path("delete_mesa/<int:pk>",login_required(deleteMesa.as_view(template_name='finales/delete_mesa.html')),name='delete_mesa'),
    path("delete_inscripcion/<int:pk>",login_required(deleteInscripcion.as_view(template_name='finales/delete_inscripcion.html')),name='delete_inscripcion'),

    #Estudiantes
    path('estudiantes/nuevo', EstudianteCreateView.as_view(), name='estudiante_nuevo'),
    path('estudiantes/<int:pk>/editar/', EstudianteUpdateView.as_view(), name='estudiante_editar'),
    path('estudiantes/<int:pk>/eliminar/', EstudianteDeleteView.as_view(), name='estudiante_eliminar'),
    path('cargaMasivaEstudiantes/',login_required(cargar_usuarios),name='cargaMasivaEstudiantes'),
    path('ver_usuario_materia/',listar_usuarios_materia,name='verUsuarioMateria'),
    # Primer logeo

     path('change_password_first/', FirstLoginPasswordChangeView.as_view(), name='first_login_password_change'),
     path('change_password_first/done/', first_login_password_change_done, name='first_login_password_change_done'),

    ###TESTING###
    path('validar-inscripcion/<int:usuario_id>/<int:materia_id>/', validar_inscripcion_final, name='validar_inscripcion_final'),
    

    path('reporte/<int:usuario_id>', reporte_estudiante_descarga, name='reporte_estudiante'),
    path('reporte_html/<int:usuario_id>', reporte_estudiante_html, name='reporte_estudiante_html'),
]

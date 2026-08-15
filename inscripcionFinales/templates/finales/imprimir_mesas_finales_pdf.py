# ══════════════════════════════════════════════════════════════
# REEMPLAZA la función imprimir_mesas_finales_pdf existente en
# inscripcionFinales/views.py (arranca cerca de la línea 1591).
# Solo cambian colores (paleta SIMEF) + la línea del instituto.
# La lógica es idéntica a la tuya.
# ══════════════════════════════════════════════════════════════

def imprimir_mesas_finales_pdf(request):
    """
    Genera un PDF con el listado de mesas de finales vigentes
    Compatible con Vercel y ambientes serverless
    """
    try:
        # Crear el PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Lista para almacenar elementos del PDF
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#0D2033'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulo
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Título principal
        elements.append(Paragraph("MESAS DE EXÁMENES FINALES", title_style))
        inst_style = ParagraphStyle(
            'Inst', parent=styles['Normal'], fontSize=12,
            textColor=colors.HexColor('#3E9BD6'), spaceAfter=2,
            alignment=TA_CENTER, fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("ISFDyT N°210 · La Plata", inst_style))
        
        # Fecha de generación
        fecha_actual = now().strftime('%d/%m/%Y %H:%M')
        elements.append(Paragraph(f"Generado el: {fecha_actual}", subtitle_style))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Obtener mesas finales vigentes
        mesas = MesaFinal.objects.select_related(
            'materia', 
            'materia__carrera',
            'materia__profesor'
        ).filter(vigente=True).order_by('llamado', 'materia__nombre_materia')
        
        if not mesas.exists():
            # Si no hay mesas, mostrar mensaje
            no_mesas_style = ParagraphStyle(
                'NoMesas',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.HexColor('#e74c3c'),
                alignment=TA_CENTER
            )
            elements.append(Paragraph("No hay mesas de finales vigentes en este momento", no_mesas_style))
        else:
            # Crear encabezados de la tabla
            data = [['Materia', 'Carrera', 'Fecha', 'Horario', 'Profesor', 'Inscripción']]
            
            # Agregar datos de cada mesa
            for mesa in mesas:
                # Determinar estado de inscripción
                inscripcion = "✓ Abierta" if mesa.inscripcionAbierta else "✗ Cerrada"
                
                # Obtener nombre del profesor
                profesor = mesa.materia.profesor.nombre_completo if mesa.materia.profesor and mesa.materia.profesor.nombre_completo else '-'
                
                # Obtener nombre de carrera
                carrera = mesa.materia.carrera.nombre_carrera if mesa.materia.carrera else '-'
                
                data.append([
                    mesa.materia.nombre_materia,
                    carrera,
                    mesa.llamado.strftime('%d/%m/%Y'),
                    mesa.llamado.strftime('%H:%M'),
                    profesor,
                    inscripcion
                ])
            
            # Crear tabla con anchos de columna personalizados
            table = Table(data, colWidths=[
                2.2*inch,  # Materia
                1.8*inch,  # Carrera
                0.9*inch,  # Fecha
                0.7*inch,  # Horario
                1.5*inch,  # Profesor
                0.9*inch   # Inscripción
            ])
            
            # Aplicar estilos a la tabla
            table.setStyle(TableStyle([
                # Estilo del encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D2033')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Estilo del cuerpo
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#3E9BD6')),
                
                # Alternancia de colores en filas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EEF3F8')]),
                
                # Padding
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
            
            # Agregar espacio y pie de página
            elements.append(Spacer(1, 0.5*inch))
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#94a3b8'),
                alignment=TA_CENTER
            )
            
            total_mesas = mesas.count()
            elements.append(Paragraph(f"Total de mesas: {total_mesas}", footer_style))
        
        # Construir el PDF
        doc.build(elements)
        
        # Obtener el contenido del PDF
        pdf = buffer.getvalue()
        buffer.close()
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="mesas_finales.pdf"'
        response.write(pdf)
        
        return response
        
    except Exception as e:
        # En caso de error, retornar mensaje descriptivo
        error_msg = f"Error al generar el PDF: {str(e)}"
        print(error_msg)  # Para logs de Vercel
        return HttpResponse(error_msg, status=500)

/** Configuración de Tailwind para SIMEF.
 *  'content' = dónde Tailwind busca las clases usadas. Si agregás plantillas
 *  en otra carpeta, sumala acá o no se incluirán sus clases en el CSS. */
module.exports = {
  content: [
    './inscripcionFinales/templates/**/*.html',
    './perfil/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        tinta:   { 50:'#EEF3F8',100:'#D6E2EE',300:'#7FA0BF',500:'#2E5478',700:'#1D3D5C',800:'#17334E',900:'#14304D',950:'#0D2033' },
        celeste: { 100:'#DDEFFA',400:'#63AFDE',500:'#3E9BD6',600:'#2C82B8' },
      },
      fontFamily: { sans: ['Archivo','system-ui','sans-serif'] },
    }
  }
}

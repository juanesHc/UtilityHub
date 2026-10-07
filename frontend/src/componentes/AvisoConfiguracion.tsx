import './avisoConfiguracion.css'

export function AvisoConfiguracion() {
  return (
    <main className="aviso-configuracion">
      <div className="logo logo--grande">
        Utility<span className="logo__ligero">Hub</span>
      </div>
      <p className="etiqueta-mono aviso-configuracion__etiqueta">Falta configuración</p>
      <h1 className="aviso-configuracion__titulo">No sé dónde está la API.</h1>
      <p className="aviso-configuracion__texto">
        Define <code>VITE_API_URL</code> con la dirección de la API: en <code>frontend/.env.development</code> para desarrollo o en{' '}
        <code>frontend/.env.production</code> antes de <code>npm run build</code>. Después reinicia el servidor de desarrollo.
      </p>
    </main>
  )
}

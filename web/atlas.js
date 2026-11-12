/* SPAIN2035_2HAB_DATOS_ACTIVADOS */
/* SPAIN 2035 — Mediterráneo de Cristal. Compatible con app_malaga.py. */
const el = id => document.getElementById(id);
const ano=el('anio'), zona=el('zona'), cp=el('cp'), tasa=el('tasa');
const importe = x => Number(x).toLocaleString('es-ES',{style:'currency',currency:'EUR'});
const mapa=L.map('mapa',{zoomSnap:.25});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(mapa);
const secciones=L.layerGroup().addTo(mapa);
let atlas,catalogo,porZona,borde,solicitud=0,datosFelicidad=null,datosCompra=null;
const escenario=()=>Number(ano.value)>2025;
const existe=(obj,k)=>Object.prototype.hasOwnProperty.call(obj||{},k);
function disponible(z){return escenario()?existe(catalogo.base2024,z):(catalogo.secciones[ano.value]||[]).includes(z);}
async function leer(url){const r=await fetch(url);if(!r.ok)throw Error('No se pudo cargar '+url);return r.json();}
function estilo(z){const activo=z===zona.value;return {color:activo?'#00a4c8':'#96b8c0',weight:activo?3:0.35,opacity:activo?1:0.20,fillColor:activo?'#3ce2e4':'#d5edf1',fillOpacity:activo?0.50:0.025};}
function centrar(){if(borde)mapa.fitBounds(borde.getBounds(),{padding:[15,15],maxZoom:15});}
function valorFelicidad(anio){
  const obs=datosFelicidad?.observaciones||{};
  if(Object.prototype.hasOwnProperty.call(obs,String(anio))){
    return {valor:Number(obs[String(anio)]),tipo:'WHR · media trianual',nota:'Resultado publicado por edición; no es una encuesta independiente de este año.'};
  }
  const pares=Object.entries(obs).map(([x,y])=>[Number(x),Number(y)])
    .filter(([x,y])=>Number.isFinite(x)&&Number.isFinite(y)&&y>=0&&y<=10)
    .sort((a,b)=>a[0]-b[0]);
  if(pares.length<4)return null;
  const n=pares.length,mx=pares.reduce((t,p)=>t+p[0],0)/n,my=pares.reduce((t,p)=>t+p[1],0)/n;
  const den=pares.reduce((t,p)=>t+(p[0]-mx)**2,0);
  if(den===0)return null;
  const pendiente=pares.reduce((t,p)=>t+(p[0]-mx)*(p[1]-my),0)/den;
  const estimacion=Math.max(0,Math.min(10,my+pendiente*(Number(anio)-mx)));
  return {valor:estimacion,tipo:'Regresión lineal · exploratoria',nota:'Extrapolación de '+n+' resultados de informes WHR; no está validada para 2035.'};
}
function actualizarFelicidad(){
  const seleccionado=Number(ano.value),resultado=valorFelicidad(seleccionado);
  el('felicidad-anio').textContent=ano.value||'—';
  el('felicidad-valor').textContent=resultado?resultado.valor.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
  el('felicidad-barra').style.width=resultado?Math.max(0,Math.min(100,resultado.valor*10))+'%':'0%';
  el('felicidad-tipo').textContent=resultado?resultado.tipo:'Proyección no disponible';
  el('felicidad-estado').textContent=resultado?resultado.nota:'Faltan valores históricos verificados para calcular la tendencia.';
  const meter=document.querySelector('.felicidad__barra');
  meter.setAttribute('aria-valuenow',resultado?String(resultado.valor):'0');
  meter.setAttribute('aria-label',resultado?'Felicidad en España: '+resultado.valor.toFixed(2)+' de 10':'Sin dato suficiente de felicidad');
}
function actualizarCompra(){
  const a=Number(ano.value),d=datosCompra||{},m2v=d.precio_compra||{};
  const m=Number(d.superficie_m2||75);
  const locales=d.valores||{};
  const porSeccion=locales[zona.value];
  const porPostal=locales[cp.value];
  const local=porSeccion||porPostal;
  const localizado=local&&Object.prototype.hasOwnProperty.call(local,String(a))
      ? Number(local[String(a)]):NaN;
  const base=Number(m2v["2026"]);
  const crecimiento=Number(d.crecimiento_escenario?.compra_pct||3.4)/100;
  let precioMetro=Number(m2v[String(a)]);
  let etiqueta="Oferta municipal · octubre "+a;
  let detalle="Málaga capital, no CP ni zona; 2 hab. de referencia · "+m+" m².";
  if(Number.isFinite(localizado)&&localizado>0){
    precioMetro=localizado;
    etiqueta=porSeccion?"Dato introducido · sección":"Dato introducido · CP "+cp.value;
    detalle="Importe local aportado; verificar fuente y que corresponda a 2 hab. · "+m+" m².";
  }else if(a>2026&&base>0){
    precioMetro=base*Math.pow(1+crecimiento,a-2026);
    etiqueta="Escenario municipal · +"+(crecimiento*100).toLocaleString("es-ES",{maximumFractionDigits:1})+" % anual";
  }
  if(Number.isFinite(precioMetro)&&precioMetro>0){
    el("compra-valor").textContent=importe(precioMetro*m);
    el("compra-etiqueta").textContent=etiqueta;
    el("compra-estado").textContent=detalle+" Precio de oferta "+importe(precioMetro)+"/m², sin impuestos ni gastos.";
  }else{
    el("compra-valor").textContent="— €";
    el("compra-etiqueta").textContent="Sin dato contrastado";
    el("compra-estado").textContent="No existe precio comparable para "+a+".";
  }
}
function actualizarReferenciaAlquiler(){
  const contenedor=el("alquiler-2hab-referencia");
  if(!contenedor)return;
  const a=Number(ano.value),d=datosCompra||{},r=d.precio_alquiler||{};
  const m=Number(d.superficie_m2||75);
  const base=Number(r["2026"]);
  const crecimiento=Number(d.crecimiento_escenario?.alquiler_pct||5.4)/100;
  let precioMetro=Number(r[String(a)]);
  let etiqueta="oferta municipal de octubre "+a;
  if(a>2026&&base>0){
    precioMetro=base*Math.pow(1+crecimiento,a-2026);
    etiqueta="escenario +"+(crecimiento*100).toLocaleString("es-ES",{maximumFractionDigits:1})+" % anual";
  }
  if(Number.isFinite(precioMetro)&&precioMetro>0){
    contenedor.textContent="2 habitaciones · "+m+" m² · "+importe(precioMetro*m)+
      "/mes (Málaga capital; "+etiqueta+").";
    contenedor.title="Precio de oferta municipal, sin desglose por código postal ni por número de dormitorios. Supuesto de superficie: "+m+" m². Fuente: idealista.";
  }else{
    contenedor.textContent="Referencia de dos habitaciones: sin dato para "+a+".";
  }
}
async function mostrar(){
  const turno=++solicitud,z=zona.value;
  if(!z)return;
  secciones.eachLayer(capa=>capa.setStyle(estilo(capa.feature.properties.CUSEC)));
  el('cp-alquiler').textContent=cp.value;
  el('anio-alquiler').textContent=ano.value;
  actualizarFelicidad();
  actualizarCompra();
  actualizarReferenciaAlquiler();
  el('modo').textContent=escenario()?'ESCENARIO · ALQUILER DE ZONA':'REGRESIÓN · ALQUILER DE ZONA';
  el('metodo').textContent=escenario()?'Mediana de zona · +2 % anual':'Mediana de zona · Gradient Boosting';
  el('lugar').textContent='CP '+cp.value+' · mediana general, no filtrada por dormitorios';
  el('detalle').textContent='';
  el('evaluacion').textContent='';
  if(!disponible(z)){
    el('estimado').textContent='Sin dato';
    el('detalle').textContent=escenario()?'No hay mediana publicada en 2024 para esta zona.':'No hay datos suficientes para calcular esta predicción.';
    return;
  }
  if(escenario()){
    const base=Number(catalogo.base2024[z]);
    const variacion=Number(tasa.value)/100;
    const alquiler=base*(1+variacion)**(Number(ano.value)-2024);
    el('estimado').textContent=importe(alquiler)+' / mes';
    el('detalle').textContent='Base observada en 2024: '+importe(base)+'. Se supone un crecimiento constante del '+tasa.value+' % anual. No es una previsión de mercado validada para '+ano.value+'.';
    return;
  }
  el('estimado').textContent='Calculando…';
  try{
    const d=await leer('/api/prediccion?anio='+encodeURIComponent(ano.value)+'&zona='+encodeURIComponent(z));
    if(turno!==solicitud)return;
    el('estimado').textContent=importe(d.estimado)+' / mes';
    el('detalle').textContent='Mediana del año anterior: '+importe(d.anterior)+'. '+(d.real==null?'Todavía no hay mediana publicada para comparar.':'Mediana publicada: '+importe(d.real)+'. Error absoluto: '+importe(Math.abs(d.real-d.estimado))+'.');
    el('evaluacion').textContent='Gradient Boosting · MAE en 2023–2024: '+importe(catalogo.mae)+'/mes.';
  }catch(err){if(turno===solicitud){el('estimado').textContent='Consulta no disponible';el('detalle').textContent='Comprueba la conexión con el servidor local.';}}
}
function dibujar(ajustar){
  const zonas=(atlas.codigos[cp.value]||[]).slice().sort();
  const anterior=zona.value;
  zona.replaceChildren(...zonas.map(z=>new Option(z,z)));
  zona.value=zonas.includes(anterior)?anterior:(zonas.find(z=>disponible(z))||zonas[0]||'');
  secciones.clearLayers();
  for(const z of zonas){
    const geo=porZona.get(z);if(!geo)continue;
    const capa=L.geoJSON(geo,{style:estilo(z)}).getLayers()[0];
    if(!capa)continue;
    capa.bindTooltip('Pulsa para consultar esta zona').on('click',()=>{zona.value=z;mostrar();});
    capa.addTo(secciones);
  }
  if(borde)mapa.removeLayer(borde);
  if(atlas.limites[cp.value])borde=L.geoJSON(atlas.limites[cp.value],{interactive:false,style:{color:'#095b9c',weight:3,dashArray:'7 5',fill:false}}).addTo(mapa);
  if(ajustar)centrar();
  mostrar();
}
async function iniciar(){
  try{
    const [datos,limites,geo]=await Promise.all(['/api/secciones','/postales.json','/secciones.json'].map(leer));
    catalogo=datos;atlas=limites;
    datosFelicidad={observaciones:{"2025": 6.54, "2015": 6.361, "2016": 6.403, "2017": 6.31, "2018": 6.354, "2019": 6.401, "2020": 6.491, "2021": 6.476, "2022": 6.436, "2023": 6.421, "2024": 6.466}};
    datosCompra={"superficie_m2": 75, "habitaciones": 2, "valores": {}, "precio_compra": {"2023": 2785, "2024": 3320, "2025": 3813, "2026": 3941}, "precio_alquiler": {"2023": 13.4, "2024": 15.8, "2025": 15.9, "2026": 16.7}, "crecimiento_escenario": {"compra_pct": 3.4, "alquiler_pct": 5.4}};
    porZona=new Map(geo.features.map(f=>[f.properties.CUSEC,f]));
    for(const codigo of Object.keys(atlas.codigos).sort())cp.add(new Option(codigo,codigo));
    for(let a=2023;a<=2035;a++)ano.add(new Option(a,a));
    cp.value=existe(atlas.codigos,'29012')?'29012':cp.options[0]?.value||'';
    ano.value='2025';
    cp.onchange=()=>dibujar(true);
    ano.onchange=()=>dibujar(false);
    zona.onchange=mostrar;
    tasa.onchange=mostrar;
    el('centrar').onclick=centrar;
    dibujar(true);
    setTimeout(()=>mapa.invalidateSize(),100);
  }catch(err){el('estimado').textContent='No se pudo abrir el atlas';el('detalle').textContent='Comprueba que el servidor sigue activo y que los datos están disponibles.';console.error(err);}
}
iniciar();


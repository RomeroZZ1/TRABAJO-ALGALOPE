// 🎯 FUNCIÓN MEJORADA: Buscar en DIAN con caché
async function buscarEnDian() {
    const partidaInput = document.getElementById('partidaInput');
    const gravamenInput = document.getElementById('gravamen');
    const ivaInput = document.getElementById('iva');
    const loader = document.getElementById('loader');
    const mensajeDiv = document.getElementById('mensaje'); // Agrega esto en tu HTML
    
    const partida = partidaInput.value.trim();
    
    // ✅ Validación mejorada
    if (!partida) {
        mostrarMensaje('Por favor ingresa una partida arancelaria', 'error');
        partidaInput.focus();
        return;
    }
    
    if (partida.length < 4) {
        mostrarMensaje('La partida debe tener al menos 4 dígitos', 'error');
        partidaInput.focus();
        return;
    }
    
    if (!/^\d+$/.test(partida)) {
        mostrarMensaje('La partida solo puede contener números', 'error');
        partidaInput.focus();
        return;
    }
    
    // Mostrar loader
    loader.style.display = 'block';
    gravamenInput.value = '';
    ivaInput.value = '';
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/consultar-arancel?partida=${partida}`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // ✅ Éxito: Llenar campos
            gravamenInput.value = data.gravamen;
            ivaInput.value = data.iva;
            
            // Mensaje diferente si vino de caché
            if (data.desde_cache) {
                mostrarMensaje('✅ Arancel encontrado (desde caché)', 'success');
            } else {
                mostrarMensaje('✅ Arancel consultado en DIAN', 'success');
            }
            
            // Opcional: Calcular automáticamente si hay valores en FOB y Flete
            calcularAutomatico();
            
        } else {
            // ❌ Error desde la API
            mostrarMensaje(`❌ ${data.error || 'No se pudo obtener el arancel'}`, 'error');
        }
        
    } catch (error) {
        console.error('Error en consulta:', error);
        mostrarMensaje('⚠️ No se pudo conectar con el servidor. Verifica que esté corriendo.', 'error');
    } finally {
        loader.style.display = 'none';
    }
}

// 🎨 Función auxiliar para mostrar mensajes
function mostrarMensaje(texto, tipo) {
    const mensajeDiv = document.getElementById('mensaje');
    
    if (!mensajeDiv) {
        // Si no existe el div, usar alert como fallback
        alert(texto);
        return;
    }
    
    mensajeDiv.textContent = texto;
    mensajeDiv.className = tipo === 'error' ? 'mensaje-error' : 'mensaje-success';
    mensajeDiv.style.display = 'block';
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
        mensajeDiv.style.display = 'none';
    }, 5000);
}

// 🧮 Función opcional: Calcular automáticamente cuando se obtiene el arancel
function calcularAutomatico() {
    const fobInput = document.getElementById('valorFOB');
    const fleteInput = document.getElementById('flete');
    
    // Solo calcular si hay valores en FOB y Flete
    if (fobInput && fleteInput && fobInput.value && fleteInput.value) {
        simularImportacion(); // Llamar a tu función de simulación
    }
}

// 📊 FUNCIÓN MEJORADA: Simular importación
async function simularImportacion() {
    const empresa = document.getElementById('empresa').value || 'Anonimo';
    const valor = parseFloat(document.getElementById('valorFOB').value) || 0;
    const flete = parseFloat(document.getElementById('flete').value) || 0;
    const gravamen = parseFloat(document.getElementById('gravamen').value) || 0;
    
    // Validaciones
    if (valor <= 0) {
        mostrarMensaje('❌ El valor FOB debe ser mayor a cero', 'error');
        return;
    }
    
    if (flete < 0) {
        mostrarMensaje('❌ El flete no puede ser negativo', 'error');
        return;
    }
    
    const loader = document.getElementById('loader');
    loader.style.display = 'block';
    
    try {
        const response = await fetch('http://127.0.0.1:5000/simular', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                empresa: empresa,
                valor: valor,
                flete: flete,
                gravamen: gravamen
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Mostrar resultados
            mostrarResultados(data);
            mostrarMensaje('✅ Simulación completada', 'success');
        } else {
            mostrarMensaje(`❌ ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error en simulación:', error);
        mostrarMensaje('⚠️ Error al procesar la simulación', 'error');
    } finally {
        loader.style.display = 'none';
    }
}

// 📈 Función para mostrar resultados de la simulación
function mostrarResultados(data) {
    // Asume que tienes elementos en tu HTML para mostrar estos datos
    const resultadosDiv = document.getElementById('resultados');
    
    if (!resultadosDiv) return;
    
    resultadosDiv.innerHTML = `
        <div class="resultado-card">
            <h3>💰 Resultados de la Simulación</h3>
            <div class="resultado-item">
                <span>CIF:</span>
                <strong>$${data.cif.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong>
            </div>
            <div class="resultado-item">
                <span>Arancel:</span>
                <strong>$${data.arancel_calculado.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong>
            </div>
            <div class="resultado-item">
                <span>IVA:</span>
                <strong>$${data.iva_calculado.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong>
            </div>
            <div class="resultado-item total">
                <span>COSTO TOTAL:</span>
                <strong>$${data.costo_total.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong>
            </div>
        </div>
    `;
    
    resultadosDiv.style.display = 'block';
}

// 📜 NUEVA FUNCIÓN: Ver historial de simulaciones
async function verHistorial() {
    const loader = document.getElementById('loader');
    loader.style.display = 'block';
    
    try {
        const response = await fetch('http://127.0.0.1:5000/historial');
        
        if (!response.ok) {
            throw new Error('Error al obtener historial');
        }
        
        const historial = await response.json();
        
        const historialDiv = document.getElementById('historial-lista');
        
        if (!historialDiv) return;
        
        if (historial.length === 0) {
            historialDiv.innerHTML = '<p>No hay simulaciones previas</p>';
            return;
        }
        
        historialDiv.innerHTML = `
            <table class="historial-table">
                <thead>
                    <tr>
                        <th>Empresa</th>
                        <th>Fecha</th>
                        <th>Costo Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${historial.map(item => `
                        <tr>
                            <td>${item.empresa}</td>
                            <td>${item.fecha}</td>
                            <td>$${item.costo_total.toLocaleString('es-CO', {minimumFractionDigits: 2})}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('⚠️ Error al cargar historial', 'error');
    } finally {
        loader.style.display = 'none';
    }
}

// 🎯 Event Listeners (agregar cuando cargue la página)
document.addEventListener('DOMContentLoaded', function() {
    
    // Buscar al presionar Enter en el campo de partida
    const partidaInput = document.getElementById('partidaInput');
    if (partidaInput) {
        partidaInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                buscarEnDian();
            }
        });
    }
    
    // Validar que solo se ingresen números en partida arancelaria
    if (partidaInput) {
        partidaInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    }
    
    // Formatear números mientras se escriben
    const numerosInputs = ['valorFOB', 'flete'];
    numerosInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('blur', function(e) {
                const valor = parseFloat(e.target.value);
                if (!isNaN(valor)) {
                    e.target.value = valor.toFixed(2);
                }
            });
        }
    });
});
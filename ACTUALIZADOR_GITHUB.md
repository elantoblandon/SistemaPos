# Actualizador con GitHub Releases

El cliente debe abrir `ActualizadorPOS.exe`. El actualizador revisa GitHub, instala cambios si existen y luego abre `SistemaPos.exe`.

## Archivos que NO se actualizan

El actualizador nunca reemplaza estos datos del cliente:

- `licorera_pro.db`
- `backups/`
- `facturas/`
- `cierres_pdf/`
- `assets/`
- `updater_config.json`
- `ActualizadorPOS.exe`

## Configurar repositorio

Edita `updater_config.json`:

```json
{
  "github_repo": "usuario/repositorio",
  "pos_exe": "SistemaPos.exe",
  "asset_name_contains": "SistemaPos",
  "allow_prereleases": false,
  "skip_update_check": false
}
```

## Crear una nueva version

1. Cambia `version.txt`, por ejemplo `1.0.1`.
2. Compila el POS:

```powershell
pyinstaller SistemaPos.spec
```

3. Crea un ZIP con los archivos de programa. Puede incluir `SistemaPos.exe`, `version.txt` y archivos auxiliares.
4. En GitHub crea un Release con tag `v1.0.1`.
5. Sube el ZIP al Release. El nombre debe contener `SistemaPos`, por ejemplo:

```text
SistemaPos_1.0.1.zip
```

## Compilar el actualizador

```powershell
pyinstaller ActualizadorPOS.spec
```

Entrega al cliente:

- `ActualizadorPOS.exe`
- `SistemaPos.exe`
- `updater_config.json`
- `version.txt`
- su `licorera_pro.db`


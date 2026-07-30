"""Lector EXPLÍCITO de cápsulas de espécimen de Study06 (onion_specimen_capsule_v1) —
read-only, sin importar código del oráculo (dependencias unidireccionales).

Transcripción fiel de specimen_capsule.py del oráculo, función por función con cita:
  _json_safe/_canonical_json  [oráculo specimen_capsule.py:68-90]
  hash_text                   [oráculo core/ids/hashing.py:11-14]
  stable_dumps                [oráculo core/ids/hashing.py:41-53]
  genome_sha256               [oráculo specimen_capsule.py:99-118]
  digest de contenido         [oráculo specimen_capsule.py:240-265]
  specimen_id                 [oráculo specimen_capsule.py:268-281]
  validación de manifiesto    [oráculo specimen_capsule.py:553-598]
  validación de arrays        [oráculo specimen_capsule.py:601-646]
  carga verificada            [oráculo specimen_capsule.py:649-696]
  re-base del ring (quench)   [oráculo specimen_capsule.py:926-937]

DECISIÓN DE ARQUITECTURA (cláusula 1 de COA): la sección `source` del manifiesto es
PROCEDENCIA OPACA — este lector no interpreta niveles de origen ni nombra sus claves de
nivel: el conjunto EXACTO de claves requeridas se valida por sha256 sellado del NOMBRE de
cada clave. El dict viaja intacto (specimen_id lo hashea tal cual) hacia el manifiesto de
procedencia del film. Naturalidad heredada: natural_unintervened=True literal, temperature=0
literal, y el genoma no puede traer overrides de laboratorio (_mem_force_scale y familia).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Mapping

import numpy as np

CAPSULE_SCHEMA = "onion_specimen_capsule_v1"
STATE_FIELDS = ("x", "v", "z", "b", "e")
ARTIFACT_FIELDS = (*STATE_FIELDS, "e_ref", "history_column", "history_head")
_ARRAY_KEYS = (*STATE_FIELDS, "e_ref_keys", "e_ref_values", "history_column", "history_head")
CLAVES_LABORATORIO = ("_b_omega_override", "_b_kcoup_override", "_mem_force_scale")

# Las 9 claves requeridas de `source` (oráculo :570-574), selladas por sha256 del nombre:
# la procedencia es OPACA — este lector valida el esquema sin nombrar niveles (cláusula 1).
_SOURCE_CLAVES_SHA = (
    "e0ddc3ac95a173ccab1ef7121a29c9fc421de953804835f4f80efc46eff0d8c9",  # harvest_semantics
    "c45353ec2c284c09fb62eab4d3df40b81671cf3d1a1d1ba1eb7773b616cb4c9f",  # harvest_tick
    "ea9d874daf229106dbe06cab7fd9b118a8bdb9d95db1fc2b694965f45bda09ff",  # history_head
    "b056b8a34929e6c557d8654fdb64231c3a7cc3ad8b57217144a9ef04cbd5df26",  # natural_unintervened
    "a7282362e3b0722ec69ffbe76a65d803374b2ba46ad68ea90e304c1033b4f1d6",  # <nivel de origen: opaca>
    "fd7827baea5589304413d836553c19c9f47e906deb6e32f90c345f5dabcf1fad",  # source_node_count
    "d4c1437ff8206dfa86cc85e803b319c3624c80d9d42bbd627342f02a080cf371",  # source_node_index
    "80b9c148b4125a9ddf723bbb641f30c35652b535c8a955f259eb5ce88fb444e6",  # source_run_id
    "b314ae60cb741e69f1cc9105ad33b19e34f608c1d2658995d648f385d7b07ac5",  # temperature
)


def _hash_text(text: str) -> str:
    """[oráculo core/ids/hashing.py:11-14]"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str:
    """[oráculo core/ids/hashing.py:24-29]"""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_safe(value: Any) -> Any:
    """[oráculo specimen_capsule.py:75-90] — mismo orden de ramas."""
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeError(f"cápsula: valor de metadata no finito: {value!r}")
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    raise RuntimeError(f"cápsula: metadata no JSON-safe: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    """[oráculo specimen_capsule.py:68-73]"""
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _stable_dumps(obj: Any, float_fmt: str = ".12g") -> str:
    """[oráculo core/ids/hashing.py:41-53]"""
    def _norm(val: Any) -> Any:
        if isinstance(val, float):
            return format(val, float_fmt)
        if isinstance(val, dict):
            return {str(k): _norm(v) for k, v in sorted(val.items(), key=lambda kv: str(kv[0]))}
        if isinstance(val, (list, tuple)):
            return [_norm(v) for v in val]
        return val
    return json.dumps(_norm(obj), sort_keys=True, separators=(",", ":"))


def genome_sha256(theta_internal: Mapping[str, Any]) -> str:
    """Huella del genoma constitutivo [oráculo :99-118]. Validación previa: schema v2, capas
    Q/S1/S2 solamente, NATURALIDAD del genoma — un theta con overrides de laboratorio
    (_mem_force_scale y familia) no es un espécimen natural y se RECHAZA acá mismo — y
    COMPLETITUD v2 (paridad con validate_theta_internal(require_v2_state=True) del oráculo
    :100-104, double tap F5 A4): sin ella, study07 aceptaba y componía genomas que el oráculo
    rechaza (S2 en modes fuera de memory.layer_order ⇒ física silenciosamente distinta)."""
    if theta_internal.get("schema_version") != "theta_internal_v2":
        raise RuntimeError("cápsula: el genoma debe ser theta_internal_v2 (legacy: RECHAZO)")
    malas = sorted(k for k in CLAVES_LABORATORIO if _contiene_clave(theta_internal, k))
    if malas:
        raise RuntimeError(f"genoma con overrides de laboratorio {malas}: no es un espécimen "
                           "natural (gate de naturalidad heredado del oráculo :294-309)")
    modos = theta_internal.get("modes") or []
    capas_malas = sorted({str(m.get("layer")) for m in modos
                          if isinstance(m, Mapping) and m.get("layer") not in {"Q", "S1", "S2"}})
    if capas_malas:
        raise RuntimeError(f"genoma con capas no transportables {capas_malas}")
    if not modos:
        raise RuntimeError("genoma v2 incompleto: sin modos")
    memoria = theta_internal.get("memory")
    struct = theta_internal.get("struct_params")
    if not (isinstance(memoria, dict) and memoria and isinstance(struct, dict) and struct):
        raise RuntimeError("genoma v2 incompleto: sin memoria o struct_params serializados "
                           "(el oráculo lo RECHAZA: require_v2_state)")
    orden = {str(n) for n in (memoria.get("layer_order") or [])}
    fuera = sorted({str(m.get("layer")) for m in modos if isinstance(m, Mapping)} - orden)
    if fuera:
        raise RuntimeError(f"genoma v2 incompleto: capas {fuera} en modes FUERA de "
                           "memory.layer_order — el oráculo lo RECHAZA "
                           "(validate_theta_internal; double tap F5 A4)")
    return f"sha256:{_hash_text(_canonical_json(theta_internal))}"


def _contiene_clave(valor: Any, clave: str) -> bool:
    if isinstance(valor, Mapping):
        return clave in valor or any(_contiene_clave(v, clave) for v in valor.values())
    if isinstance(valor, (list, tuple)):
        return any(_contiene_clave(v, clave) for v in valor)
    return False


def _update_array_digest(digest, key: str, array: np.ndarray) -> None:
    """[oráculo specimen_capsule.py:240-251] — byte a byte el mismo protocolo."""
    digest.update(key.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(_stable_dumps(list(array.shape)).encode("ascii"))
    digest.update(b"\0")
    if array.dtype.kind == "U":
        digest.update(_stable_dumps(array.tolist()).encode("utf-8"))
    else:
        digest.update(np.ascontiguousarray(array).tobytes(order="C"))
    digest.update(b"\0")


def state_content_sha256(arrays: Mapping[str, np.ndarray]) -> str:
    """[oráculo specimen_capsule.py:254-258]"""
    digest = hashlib.sha256()
    for key in _ARRAY_KEYS:
        _update_array_digest(digest, key, np.asarray(arrays[key]))
    return f"sha256:{digest.hexdigest()}"


def specimen_id(manifest: Mapping[str, Any]) -> str:
    """[oráculo specimen_capsule.py:268-281] — la identidad hashea `source` OPACO, tal cual."""
    identidad = {
        "schema_version": manifest["schema_version"],
        "block_id": manifest["block_id"],
        "genome_hash": manifest["genome_hash"],
        "source": manifest["source"],
        "engine_contract": manifest["engine_contract"],
        "state_content_sha256": manifest["state_artifact"]["content_sha256"],
        "lineage": manifest["lineage"],
    }
    return f"onion-{_hash_text(_canonical_json(identidad))[:24]}"


def _validar_manifiesto(manifest: Any) -> Dict[str, Any]:
    """[oráculo specimen_capsule.py:553-598] — mismas exigencias, fail-loud."""
    if not isinstance(manifest, dict):
        raise RuntimeError("cápsula: el manifiesto debe ser un objeto")
    requeridas = {"schema_version", "specimen_id", "block_id", "genome_hash", "source",
                  "engine_contract", "state_artifact", "lineage"}
    faltan = sorted(requeridas - set(manifest))
    if faltan:
        raise RuntimeError(f"cápsula: manifiesto sin claves {faltan}")
    if manifest.get("schema_version") != CAPSULE_SCHEMA:
        raise RuntimeError(f"cápsula: schema no soportado {manifest.get('schema_version')!r}")
    source = manifest["source"]; engine = manifest["engine_contract"]
    artifact = manifest["state_artifact"]
    if not (isinstance(source, dict) and isinstance(engine, dict) and isinstance(artifact, dict)):
        raise RuntimeError("cápsula: source/engine_contract/state_artifact deben ser objetos")
    presentes = {_hash_text(str(k)) for k in source}
    faltan_src = [h for h in _SOURCE_CLAVES_SHA if h not in presentes]
    if faltan_src:
        raise RuntimeError(f"cápsula: source no cumple el esquema v1 — faltan "
                           f"{len(faltan_src)} clave(s) requerida(s) (presentes: "
                           f"{sorted(source)}); la procedencia se valida por hash sellado "
                           "del nombre (procedencia OPACA, cláusula 1)")
    engine_req = {"dt", "delay_steps", "k_global", "gamma_c", "emission_scale",
                  "engine_params", "topology_hash"}
    faltan_eng = sorted(engine_req - set(engine))
    if faltan_eng:
        raise RuntimeError(f"cápsula: engine_contract sin claves {faltan_eng}")
    faltan_art = sorted({"path", "sha256", "content_sha256", "fields"} - set(artifact))
    if faltan_art:
        raise RuntimeError(f"cápsula: state_artifact sin claves {faltan_art}")
    if source["natural_unintervened"] is not True or float(source["temperature"]) != 0.0:
        raise RuntimeError("cápsula: no es un espécimen natural determinista "
                           "(natural_unintervened debe ser True y temperature 0.0)")
    if int(source["source_node_count"]) <= 0:
        raise RuntimeError("cápsula: source_node_count debe ser positivo")
    if int(source["source_node_index"]) not in range(int(source["source_node_count"])):
        raise RuntimeError("cápsula: source_node_index inconsistente con source_node_count")
    if float(engine["dt"]) <= 0.0 or int(engine["delay_steps"]) < 0:
        raise RuntimeError("cápsula: dt o delay_steps inválidos en engine_contract")
    if artifact["fields"] != list(ARTIFACT_FIELDS):
        raise RuntimeError("cápsula: state_artifact.fields no coincide con el contrato v1")
    return manifest


def _validar_arrays(path: Path, delay_steps: int) -> Dict[str, np.ndarray]:
    """[oráculo specimen_capsule.py:601-646] — mismas exigencias, en el mismo orden."""
    try:
        with np.load(path, allow_pickle=False) as stored:
            if set(stored.files) != set(_ARRAY_KEYS):
                raise RuntimeError(f"cápsula: claves del state artifact "
                                   f"esperadas={sorted(_ARRAY_KEYS)} reales={sorted(stored.files)}")
            arrays = {k: np.array(stored[k], copy=True) for k in _ARRAY_KEYS}
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"cápsula: no se puede leer {path}: {exc}") from exc
    for key in (*STATE_FIELDS, "e_ref_values", "history_column"):
        if arrays[key].dtype != np.dtype(np.float64):
            raise RuntimeError(f"cápsula: {key} debe ser float64, es {arrays[key].dtype}")
        if not np.all(np.isfinite(arrays[key])):
            raise RuntimeError(f"cápsula: {key} con valores no finitos")
    for key in STATE_FIELDS:
        if arrays[key].ndim != 1:
            raise RuntimeError(f"cápsula: {key} debe ser 1-D")
    if arrays["x"].shape != arrays["v"].shape:
        raise RuntimeError("cápsula: x y v difieren en forma")
    if arrays["b"].shape != arrays["e"].shape:
        raise RuntimeError("cápsula: b y e difieren en forma")
    if arrays["e_ref_keys"].dtype.kind != "U" or arrays["e_ref_keys"].ndim != 1:
        raise RuntimeError("cápsula: e_ref_keys debe ser 1-D Unicode")
    if arrays["e_ref_values"].shape != arrays["e_ref_keys"].shape:
        raise RuntimeError("cápsula: e_ref keys/values difieren en forma")
    keys = [str(v) for v in arrays["e_ref_keys"]]
    if len(keys) != len(set(keys)) or len(keys) != arrays["b"].size:
        raise RuntimeError("cápsula: e_ref debe ser único y cubrir cada capa lenta")
    esperado = (int(delay_steps) + 1, 2)
    if arrays["history_column"].shape != esperado:
        raise RuntimeError(f"cápsula: history_column {arrays['history_column'].shape} != {esperado}")
    if arrays["history_head"].dtype != np.dtype(np.int64) or arrays["history_head"].shape != ():
        raise RuntimeError("cápsula: history_head debe ser int64 escalar")
    head = int(arrays["history_head"])
    if head < 0 or head >= esperado[0]:
        raise RuntimeError(f"cápsula: history_head fuera de rango: {head}")
    for a in arrays.values():
        a.setflags(write=False)
    return arrays


def load_capsule(path: Path | str) -> Dict[str, Any]:
    """Carga y VERIFICA una cápsula sin tocar ningún motor [oráculo :649-696]. Devuelve
    {manifest, arrays, capsule_sha256, dir} con arrays read-only. Verifica: forma del
    manifiesto · hash del archivo state.npz · hash de CONTENIDO de los arrays · consistencia
    de history_head · invariante de emisión history_column[head] == scale·[Σx, Σv] BIT-exacto ·
    specimen_id recomputado. Cualquier discrepancia = fail-loud."""
    path = Path(path)
    manifest_path = (path / "capsule.json" if path.is_dir() else path).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"cápsula: no se puede leer {manifest_path}: {exc}") from exc
    manifest = _validar_manifiesto(manifest)
    rel = Path(str(manifest["state_artifact"]["path"]))
    if rel.is_absolute():
        raise RuntimeError("cápsula: el state artifact debe ser relativo a la cápsula")
    artifact_path = (manifest_path.parent / rel).resolve()
    try:
        artifact_path.relative_to(manifest_path.parent)
    except ValueError as exc:
        raise RuntimeError("cápsula: el state artifact escapa del directorio") from exc
    esperado = str(manifest["state_artifact"]["sha256"])
    real = f"sha256:{_hash_file(artifact_path)}"
    if real != esperado:
        raise RuntimeError(f"cápsula: hash del state artifact {real} != manifiesto {esperado}")
    arrays = _validar_arrays(artifact_path, int(manifest["engine_contract"]["delay_steps"]))
    contenido = state_content_sha256(arrays)
    if contenido != manifest["state_artifact"]["content_sha256"]:
        raise RuntimeError("cápsula: hash de CONTENIDO del estado no coincide")
    if int(arrays["history_head"]) != int(manifest["source"]["history_head"]):
        raise RuntimeError("cápsula: history_head difiere entre manifiesto y state artifact")
    head = int(arrays["history_head"])
    scale = float(manifest["engine_contract"]["emission_scale"])
    emision = scale * np.array([np.sum(arrays["x"]), np.sum(arrays["v"])], dtype=np.float64)
    if not np.array_equal(arrays["history_column"][head], emision):
        raise RuntimeError("cápsula: la emisión actual del ring es inconsistente con el "
                           "estado x/v sellado (invariante del oráculo :677-685)")
    esperado_id = specimen_id(manifest)
    if manifest["specimen_id"] != esperado_id:
        raise RuntimeError(f"cápsula: specimen_id {manifest['specimen_id']} != recomputado "
                           f"{esperado_id}")
    return {"manifest": copy.deepcopy(manifest), "arrays": arrays,
            "capsule_sha256": f"sha256:{_hash_file(manifest_path)}",
            "dir": str(manifest_path.parent)}


def quench_column(arrays: Mapping[str, np.ndarray], target_delay_steps: int) -> np.ndarray:
    """Re-base cronológico del ring al head=0 del receptor, truncando a SU delay
    [oráculo specimen_capsule.py:926-937]. Extrapolar está PROHIBIDO: la cápsula debe traer
    al menos target_delay_steps de historia [oráculo :866-870]."""
    source = np.asarray(arrays["history_column"])
    head = int(arrays["history_head"])
    source_delay = source.shape[0] - 1
    target_delay_steps = int(target_delay_steps)
    if source_delay < target_delay_steps:
        raise RuntimeError(f"quench: el receptor exige {target_delay_steps} pasos de historia "
                           f"pero la cápsula trae {source_delay}; extrapolar está prohibido")
    size = target_delay_steps + 1
    columna = np.empty((size, 2), dtype=np.float64)
    for steps_ago in range(target_delay_steps + 1):
        columna[(-steps_ago) % size] = source[(head - steps_ago) % source.shape[0]]
    return columna

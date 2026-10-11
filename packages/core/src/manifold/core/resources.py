"""Typed resource slots (proposed): what an engine declares it can use, what a run requests, what a backend
advertises, and how a backend grants a request.

Slots: `cpu_threads` (a count; an adapter declares a range and the environment variables that carry the count),
`memory_bytes`, `gpu` (a count, an optional device class, an optional memory per device), `scratch_bytes`, `network`
(`none`, the default, or `allow`), `assets` (named, hashed library inputs; section 7.4 of the CONOPS) and `interpreter`
(an external environment the engine runs in). An adapter's `resources()` returns a `ResourceDeclaration`; a run spec
records its requests in the optional top-level `resources` member (`parse_request`); a backend advertises a
`Capacity`. `check(request, declaration, capacity)` gives the admission problems (a request the engine cannot honor
or the backend cannot provide, for example a GPU on a backend with none); `allocate(request, capacity, in_use)` gives
a `Grant` or None (wait), so concurrent runs never exceed the capacity.

Identity: a slot that can change a run's result (`cpu_threads`, `gpu`, `assets`, `interpreter`) is part of the run id
when the run spec states it; a slot that cannot (`memory_bytes`, `scratch_bytes`, `network`) is not (`ID_SLOTS`,
`identity_view`). A run spec without `resources` has the id it had before the slots existed.

Imports: the standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SLOTS = ("cpu_threads", "memory_bytes", "gpu", "scratch_bytes", "network", "assets", "interpreter")
ID_SLOTS = ("cpu_threads", "gpu", "assets", "interpreter")          # slots that can change the result
NETWORK = ("none", "allow")


@dataclass(frozen=True)
class CpuThreads:
    """The thread counts an engine can run with: `minimum`..`maximum` (None: no upper bound), `default` when a run
    requests none (None: the engine's own default, not reserved), and the environment `variables` set to the count."""
    minimum: int = 1
    maximum: int | None = None
    default: int | None = None
    variables: tuple = ()


@dataclass(frozen=True)
class GpuSlot:
    """GPUs an engine can use: up to `maximum` devices of `device_class` (None: any) with `memory_bytes` each."""
    maximum: int = 0
    device_class: str | None = None
    memory_bytes: int | None = None


@dataclass(frozen=True)
class AssetDecl:
    """A named external input an engine needs: a library reference `{name, content_hash}` (a file's sha256 or a
    directory's `dirhash/1` digest) and where the engine expects to find it (`env`: a variable the launch plan sets to
    the staged path)."""
    name: str
    ref: dict
    env: str | None = None
    description: str = ""


@dataclass(frozen=True)
class ResourceDeclaration:
    """What an adapter declares (see the module docstring)."""
    cpu_threads: CpuThreads = field(default_factory=CpuThreads)
    memory_bytes: int | None = None
    gpu: GpuSlot = field(default_factory=GpuSlot)
    scratch_bytes: int | None = None
    network: str = "none"
    assets: tuple = ()
    interpreter: str | None = None


@dataclass(frozen=True)
class GpuRequest:
    count: int = 0
    device_class: str | None = None
    memory_bytes: int | None = None


@dataclass(frozen=True)
class ResourceRequest:
    """A run's requests, from the run spec's `resources` member."""
    cpu_threads: int | None = None
    memory_bytes: int | None = None
    gpu: GpuRequest = field(default_factory=GpuRequest)
    scratch_bytes: int | None = None
    network: str = "none"
    assets: tuple = ()
    interpreter: str | None = None


@dataclass(frozen=True)
class GpuDevice:
    device_id: str
    device_class: str | None = None
    memory_bytes: int | None = None


@dataclass(frozen=True)
class Capacity:
    """What a backend advertises: CPU threads, memory, GPU devices (an empty tuple: none), scratch space, whether the
    site allows network access."""
    cpu_threads: int
    memory_bytes: int | None = None
    gpus: tuple = ()
    scratch_bytes: int | None = None
    network: bool = False


@dataclass(frozen=True)
class Grant:
    """What a backend reserved for one run: threads (None: the engine's default, not reserved), memory, GPU ids."""
    cpu_threads: int | None = None
    memory_bytes: int = 0
    gpu_ids: tuple = ()


def _int(value, where, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"resources.{where} is {value!r}; expected an integer >= {minimum}")
    return value


def parse_request(member):
    """The `ResourceRequest` of a run spec's `resources` member (None or absent: no requests). ValueError names the
    member at fault."""
    if member is None:
        return ResourceRequest()
    if not isinstance(member, dict):
        raise ValueError(f"resources is {type(member).__name__}; expected a mapping")
    unknown = sorted(set(member) - set(SLOTS))
    if unknown:
        raise ValueError(f"resources has unknown slots {unknown}; the slots are {list(SLOTS)}")
    gpu = member.get("gpu")
    if gpu is not None:
        if not isinstance(gpu, dict):
            raise ValueError("resources.gpu must be a mapping {count, device_class?, memory_bytes?}")
        gpu = GpuRequest(_int(gpu.get("count", 1), "gpu.count", 0), gpu.get("device_class"),
                         None if gpu.get("memory_bytes") is None else _int(gpu["memory_bytes"], "gpu.memory_bytes"))
    network = member.get("network", "none")
    if network not in NETWORK:
        raise ValueError(f"resources.network is {network!r}; expected one of {list(NETWORK)}")
    assets = member.get("assets") or ()
    if not isinstance(assets, (list, tuple)) or not all(isinstance(a, dict) and isinstance(a.get("name"), str)
                                                        for a in assets):
        raise ValueError("resources.assets must be a list of {name, ref: {name, content_hash}}")
    return ResourceRequest(
        cpu_threads=None if member.get("cpu_threads") is None else _int(member["cpu_threads"], "cpu_threads", 1),
        memory_bytes=None if member.get("memory_bytes") is None else _int(member["memory_bytes"], "memory_bytes"),
        gpu=gpu or GpuRequest(),
        scratch_bytes=None if member.get("scratch_bytes") is None else _int(member["scratch_bytes"], "scratch_bytes"),
        network=network, assets=tuple(assets), interpreter=member.get("interpreter"))


def _matching(devices, request):
    return [d for d in devices
            if (request.device_class is None or d.device_class == request.device_class)
            and (request.memory_bytes is None or (d.memory_bytes or 0) >= request.memory_bytes)]


def check(request, declaration, capacity=None):
    """Admission problems (strings) for a request the engine does not declare or, with a `capacity`, the backend
    cannot provide."""
    out = []
    t = request.cpu_threads
    if t is not None:
        decl = declaration.cpu_threads
        if t < decl.minimum or (decl.maximum is not None and t > decl.maximum):
            out.append(f"resources.cpu_threads is {t}; the engine runs with {decl.minimum} to "
                       f"{decl.maximum if decl.maximum is not None else 'any number of'} threads")
        if capacity is not None and t > capacity.cpu_threads:
            out.append(f"resources.cpu_threads is {t}; this backend has {capacity.cpu_threads}")
    if capacity is not None and request.memory_bytes is not None and capacity.memory_bytes is not None and \
            request.memory_bytes > capacity.memory_bytes:
        out.append(f"resources.memory_bytes is {request.memory_bytes}; this backend has {capacity.memory_bytes}")
    g = request.gpu
    if g.count:
        if g.count > declaration.gpu.maximum:
            out.append(f"resources.gpu requests {g.count} GPU(s); the engine declares at most {declaration.gpu.maximum}")
        matching = _matching(capacity.gpus, g) if capacity is not None else None
        if matching is not None and g.count > len(matching):
            what = f"{g.count} GPU(s)" + (f" of class {g.device_class!r}" if g.device_class else "") + \
                (f" with {g.memory_bytes} bytes" if g.memory_bytes else "")
            out.append(f"resources.gpu requests {what}; this backend advertises "
                       f"{len(matching) if capacity.gpus else 'no'} matching GPU(s)")
    if capacity is not None and request.scratch_bytes is not None and capacity.scratch_bytes is not None and \
            request.scratch_bytes > capacity.scratch_bytes:
        out.append(f"resources.scratch_bytes is {request.scratch_bytes}; this backend has {capacity.scratch_bytes}")
    if request.network == "allow":
        if declaration.network == "none":
            out.append("resources.network is allow; the engine declares no network use")
        elif capacity is not None and not capacity.network:
            out.append("resources.network is allow; this backend allows no network access")
    if request.interpreter is not None and request.interpreter != declaration.interpreter:
        out.append(f"resources.interpreter is {request.interpreter!r}; the engine runs in "
                   f"{declaration.interpreter or 'the SDK interpreter'}")
    return out


def allocate(request, declaration, capacity, in_use):
    """A `Grant` for `request` given the grants `in_use`, or None when it does not fit now (wait and retry). Assumes
    `check` passed."""
    threads = request.cpu_threads if request.cpu_threads is not None else declaration.cpu_threads.default
    used_threads = sum(g.cpu_threads or 0 for g in in_use)
    if threads is not None and used_threads + threads > capacity.cpu_threads:
        return None
    memory = request.memory_bytes or 0
    if capacity.memory_bytes is not None and sum(g.memory_bytes for g in in_use) + memory > capacity.memory_bytes:
        return None
    gpu_ids = ()
    if request.gpu.count:
        taken = {i for g in in_use for i in g.gpu_ids}
        free = [d for d in _matching(capacity.gpus, request.gpu) if d.device_id not in taken]
        if len(free) < request.gpu.count:
            return None
        gpu_ids = tuple(d.device_id for d in free[:request.gpu.count])
    return Grant(threads, memory, gpu_ids)


def identity_view(resources_member):
    """The part of a run spec's `resources` member that enters the run id (`ID_SLOTS`), or None when nothing does."""
    if not isinstance(resources_member, dict):
        return resources_member
    kept = {k: v for k, v in resources_member.items() if k in ID_SLOTS}
    return kept or None


def as_dict(obj):
    """A declaration, request, grant or capacity as plain JSON-ready data."""
    from dataclasses import asdict, is_dataclass
    return asdict(obj) if is_dataclass(obj) else obj

{ inputs }:

final: prev: {
  adaptive-os = prev.python3Packages.buildPythonApplication {
    pname = "adaptive-os";
    version = inputs.self.shortRev or "dev";
    format = "pyproject";

    src = inputs.self + "/orchestrator";

    nativeBuildInputs = with prev.python3Packages; [
      setuptools
      setuptools-scm
    ];

    propagatedBuildInputs = with prev.python3Packages; [
      aiohttp
      aiosqlite
      click
      httpx
      psutil
      pydantic
      pyyaml
      rich
      watchdog
    ];

    doCheck = false;   # tests need live Ollama; run separately with nix develop

    meta = {
      description = "AI-driven system orchestrator that adapts your OS to your context";
      homepage    = "https://github.com/Ivan-IA17/adaptive-os";
      license     = prev.lib.licenses.mit;
      maintainers = [ ];
      mainProgram = "adaptive-os";
    };
  };
}

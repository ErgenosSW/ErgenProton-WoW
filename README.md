# ErgenProton-WoW

ErgenProton-WoW is a focused [GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom) derivative for running Battle.net and World of Warcraft on Linux through [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher).

The project currently targets World of Warcraft Retail. Classic support and broader hardware coverage still require validation.

> [!IMPORTANT]
> ErgenProton-WoW is an independent community project. It is not affiliated with or supported by Valve, GloriousEggroll, Blizzard Entertainment, or CodeWeavers. Report problems caused by this build here, not to the upstream GE-Proton or Valve issue trackers.

## Current optimization

The `umu-wow` compatibility profile applies:

```text
WINE_SIMULATE_WRITECOPY=1
```

This is deliberately a small, measurable change. The project does not enable a collection of unverified “gaming tweaks.” Future changes should be added only after controlled testing shows a reproducible benefit or fixes a real compatibility problem.

## Benchmark result

A controlled World of Warcraft Retail test was performed on September 20, 2026. Each result below is the mean of three static 60-second MangoHud captures taken in the same Silvermoon location with the same camera and graphics settings.

| Runner | Average FPS | 1% low | 0.1% low | Average frame time |
| --- | ---: | ---: | ---: | ---: |
| GE-Proton11-7, faster comparison block | 77.3 | 55.1 | 43.3 | 12.93 ms |
| ErgenProton-WoW 0.1.0-dev | **81.8** | **60.4** | **46.3** | **12.20 ms** |
| ErgenProton-WoW with WriteCopy disabled | 74.0 | 55.2 | 34.6 | 13.50 ms |

Against the faster GE-Proton comparison block, ErgenProton-WoW produced approximately:

- 5.8% higher average FPS
- 9.5% higher 1% low
- 7.0% higher 0.1% low
- 5.7% lower average frame time

Enabling `WINE_SIMULATE_WRITECOPY` in the same ErgenProton build increased average FPS by approximately 10.6% over the disabled control.

These numbers describe one system, one game version, one location, and one set of settings. They demonstrate a useful result on the tested machine, not guaranteed performance on every Linux configuration. The 0.1% low result is particularly sensitive to background activity and in-game population.

## Installation

### Steam compatibility tools directory

1. Download the `.tar.gz` archive and matching `.sha512sum` file from the project release or workflow artifact.
2. Verify the archive from the directory containing both files:

   ```bash
   sha512sum -c ErgenProton-WoW-*.sha512sum
   ```

3. Create the compatibility tools directory:

   ```bash
   mkdir -p ~/.local/share/Steam/compatibilitytools.d
   ```

4. Extract the archive:

   ```bash
   tar -xzf ErgenProton-WoW-*.tar.gz \
     -C ~/.local/share/Steam/compatibilitytools.d
   ```

5. Restart Steam and any launcher that reads Steam compatibility tools.

### Faugus Launcher

Select the installed ErgenProton-WoW build as the Battle.net runner and use:

```text
UMU ID: umu-wow
```

The `umu-wow` profile supplies `WINE_SIMULATE_WRITECOPY=1`; do not add the same variable manually.

Confirm the active configuration while Battle.net is running:

```bash
pid=$(pgrep -n -f 'Battle.net.exe')

tr '\0' '\n' < "/proc/$pid/environ" |
  grep -E '^(PROTONPATH|UMU_ID|GAMEID|WINE_SIMULATE_WRITECOPY)='
```

The output should identify ErgenProton-WoW and contain:

```text
UMU_ID=umu-wow
GAMEID=umu-wow
WINE_SIMULATE_WRITECOPY=1
```

> [!WARNING]
> Non-Steam applications should run through umu-launcher. Launching Proton directly without its expected container runtime is unsupported and can cause library incompatibilities.

## Tested status

| Component | Status |
| --- | --- |
| Battle.net | Launches successfully |
| World of Warcraft Retail | Launches and benchmarked |
| World of Warcraft Classic | Testing planned |
| World of Warcraft Forever | Not tested; testing begins after release |
| Secure Boot | Unrelated to this compatibility tool |

## Development builds

Development builds are produced by the `Development` GitHub Actions workflow. Their names include the source commit, for example:

```text
ErgenProton-WoW-0.1.0-dev-94e14f45
```

Builds from development branches are test candidates, not stable releases.

## Building

Clone the repository with all submodules:

```bash
git clone --recurse-submodules \
  https://github.com/ErgenosSW/ErgenProton-WoW.git
```

The build system is inherited from GE-Proton. Refer to the upstream [GE-Proton build documentation](https://github.com/GloriousEggroll/proton-ge-custom#building) for local build requirements. This repository also provides GitHub Actions workflows for reproducible development artifacts.

## Reporting problems

When opening an issue, include:

- ErgenProton-WoW version
- WoW edition: Retail or Classic
- GPU and driver version
- desktop session: Wayland or X11
- launcher and umu-launcher version
- whether the problem also occurs with the matching GE-Proton base
- relevant terminal output or Proton log

Do not report ErgenProton-WoW-specific problems to Valve or GE-Proton unless the same problem is reproducible with their unmodified build.

## Upstream and licenses

ErgenProton-WoW is built on the work of:

- [GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom) by GloriousEggroll and its contributors
- [Proton](https://github.com/ValveSoftware/Proton) by Valve and its contributors
- [Wine](https://www.winehq.org/) and Wine Staging
- [umu-launcher and umu-protonfixes](https://github.com/Open-Wine-Components)
- DXVK, VKD3D-Proton and the other upstream projects included by Proton and GE-Proton

The repository contains components under multiple licenses. See [`LICENSE`](LICENSE), [`LICENSE.proton`](LICENSE.proton), and the license files shipped with individual components.

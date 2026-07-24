---
name: wuhoo-unity-ci-pitfalls
description: "Diagnose Unity CI build failures and runtime feature-regression bugs specific to the wuhoo miners-watch pipeline — Android Package Name, runner disk space (with cleanup fix), cache invalidation, hidden compiler errors, test threshold consistency, missing using/asmdef directives, stale scenes causing missing runtime features, empty Release assets, duplicate CI runs, wave index gaps, Volume NRE, Font allocation leaks. 15 pitfalls total. Companion to wuhoo-game-dev-daily-build."
version: 1.1.0
---

# Wuhoo Unity CI Pitfalls

Fast diagnosis for miners-watch CI failures on GitHub Actions. Ordered by observed frequency.

## Android Package Name

**Symptom**: `UnityException: Package Name has not been set up correctly`
**Root cause**: Non-ASCII productName in ProjectSettings.asset. Unity auto-derives invalid Android bundle identifier.
**Fix**: Explicit `applicationIdentifier: {Android: com.minerswatch.game}` in ProjectSettings.asset.
**Prevention**: Never change productName to non-ASCII without also setting applicationIdentifier.

## Runner Disk Space

**Symptom**: `no space left on device` or exit code 101 (OOM).
**Diagnosis**: Win64 ✅ + QG ✅ + no CS errors → infra issue. Do NOT change code. Retry.
**Fix (2026-07-24)**: Added disk cleanup step before ALL build jobs:
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL
    sudo docker image prune --all --force || true
    df -h /
```
This reclaims ~8-10GB. Applied to both main build matrix and Android Debug job.

## Matrix Job Visibility

**Pitfall**: `gh run list` shows Build conclusion as blank while some matrix jobs already failed. `gh run view --json jobs` reveals per-job status.
**Rule**: Always check individual jobs before claiming "CI green":
```bash
gh run view <id> --json jobs -q '.jobs[] | "\(.name) \(.conclusion)"'
```
Only when ALL jobs show success is CI truly green. Partial success (Win64 only) is NOT green. This caused a premature release claim in 2026-07-21 session — user caught it.

## Hidden Compiler Errors

**Symptom**: Build summary shows "Scripts have compiler errors" with no line numbers.
**Fix**: `gh run view <id> --log-failed | grep "error CS"`

## FindObjectOfType Deprecation (Unity 6 CS0618)

**Symptom**: Unity Console flooded with `warning CS0618: 'Object.FindObjectOfType<T>()' is obsolete: 'Use FindAnyObjectByType instead.'`

**Root cause**: Unity 6 deprecated `FindObjectOfType<T>()` in favor of `FindAnyObjectByType<T>()`. The new API also finds inactive objects (broader search).

**Fix**: Replace all occurrences across the codebase:
```bash
search_files pattern="FindObjectOfType" target=content path=Assets/Scripts
```
Then replace each with `FindAnyObjectByType`. Semantics are equivalent for active-object lookups; the only difference is the new API also matches inactive objects.

**Safe patterns** (no behavior change):
- `FindObjectOfType<X>()` → `FindAnyObjectByType<X>()`
- `GetComponent<X>() ?? FindObjectOfType<X>()` → `GetComponent<X>() ?? FindAnyObjectByType<X>()`

**Real case (2026-07-24)**: 12 occurrences across 8 files (GameRoot, SceneController, DayNightPostProcess, MainMenuUI, SettingsUI, GameOverUI, CaveEntryUI, ReturnToSurface). All replaced in a single commit. Zero behavior change, zero regression, 142/142 tests pass.

## ASMDEF Missing Assembly Reference — CS0246 for URP / Rendering Types

**Symptom**: CS0246 errors for URP types (`Volume`, `Bloom`, `Vignette`, `ColorAdjustments`) despite correct `using` directives in the C# file:
```
error CS0246: The type or namespace name 'Volume' could not be found
```

**Root cause**: The project uses an `.asmdef` that doesn't reference the required Unity package assemblies. URP types need TWO separate assemblies:
- `Unity.RenderPipelines.Core.Runtime` — `Volume`, `VolumeProfile` (base types)
- `Unity.RenderPipelines.Universal.Runtime` — `Bloom`, `Vignette`, `ColorAdjustments`

Adding only `Universal.Runtime` is insufficient — `Volume` lives in `Core.Runtime`.

**Fix**: Add BOTH:
```json
"references": [
    "Unity.RenderPipelines.Core.Runtime",
    "Unity.RenderPipelines.Universal.Runtime"
]
```

**Real case (2026-07-22)**: Added `DayNightPostProcess.cs` using URP types. First commit only had `Unity.RenderPipelines.Universal.Runtime` → CI QG failed. Added `Core.Runtime` → fixed.

## Cold Build After ProjectSettings Change

**Symptom**: Build time 2-3x normal.
**Cause**: `hashFiles('ProjectSettings/**')` in cache key invalidates Library cache.
**Response**: Expected. QG proves correctness; wait for Build.

## Test Threshold Consistency

When changing game config values (e.g. 500→50):
1. `search_files` for old numeric literals in `Assets/Tests/`
2. Update ALL hardcoded test values
3. Update `AccumulatedGold` test totals if they cross threshold
4. Sweep for remaining old values

## Missing `using UnityEngine.UI`

Adding Text/Image/Button/Slider to Editor scene-author scripts requires `using UnityEngine.UI;`. CS0246 otherwise.

## Duplicate Assets — Wrong Directory for Resources.Load

**Symptom**: `Resources.Load("Audio/SFX/sfx_mine_01")` returns null at runtime, but the file exists in `Assets/Audio/SFX/`.
**Root cause**: Unity's `Resources.Load()` ONLY searches under `Assets/Resources/`. Files in `Assets/Audio/` are NOT accessible at runtime.
**Fix**: Copy files to `Assets/Resources/Audio/`, then delete the original `Assets/Audio/` directory to avoid confusion and duplicated build weight (14 WAVs × 2 = ~500KB wasted).
**Prevention**: When creating runtime-loaded assets via `Resources.Load()`, always place them under `Assets/Resources/<path>/`. Never keep duplicates.

## Stale EditorBuildSettings After Scene Removal

**Symptom**: Build warning about missing `TestGround.unity`, or build includes a retired scene.
**Root cause**: Deleting `Assets/Scenes/TestGround.unity` without removing it from `ProjectSettings/EditorBuildSettings.asset`.
**Fix**: Edit `EditorBuildSettings.asset` to remove the scene entry. Verify with `search_files pattern="TestGround" target=content path=ProjectSettings`.

## Release Assets Empty — Build Succeeds But APK Never Uploaded

**Symptom**: User reports "new features not working" despite CI all-green and code committed. GitHub Release page shows the release exists but has **zero assets** (no APK files). User unknowingly downloads an older release that still has files.

**Diagnostic flow**:
```bash
# 1. Check what the user likely downloaded
gh release list --repo wuhoo-ai/miners-watch --limit 5

# 2. Verify asset count per release
for tag in v1.2-preview.1 v1.1-preview.9 v1.1-preview.8; do
  echo "=== $tag ==="
  gh api repos/wuhoo-ai/miners-watch/releases/tags/$tag --jq '.assets | length'
done

# 3. Confirm CI artifacts exist (they do — just not on Release)
gh run view <run_id> --repo wuhoo-ai/miners-watch --json jobs -q '.jobs[] | "\(.name) [\(.conclusion)]"'
gh api repos/wuhoo-ai/miners-watch/actions/runs/<run_id>/artifacts --jq '.artifacts[] | "\(.name) id=\(.id) \(.size_in_bytes) bytes"'

# 4. Download artifact and upload to Release
gh run download <run_id> --name Build-Android --dir /tmp/apk
gh release upload <tag> /tmp/apk/Android.apk --repo wuhoo-ai/miners-watch
```

**Root cause**: CI workflow (`.github/workflows/build.yml`) only runs `actions/upload-artifact@v4` → files land in GitHub Actions **temporary storage** (7-day retention). There is **no step** that uploads the APK to the GitHub Release. The Release is created separately (manually or via another automation) but nobody pushes the build output into it.

**Fix**: Add a release-upload step to the workflow, or create a separate release workflow triggered on tag push. Example step:
```yaml
- name: Upload to Release
  if: startsWith(github.ref, 'refs/tags/')
  uses: softprops/action-gh-release@v2
  with:
    files: build/Android/*.apk
```

**Prevention**: After creating a release, always verify: `gh release view <tag> --json assets -q '.assets | length'` must return > 0.

## Stale Private Methods After Feature Replacement

**Symptom**: No compiler warning, but the codebase has unused dead methods.
**Pattern**: When replacing a feature (e.g., `GetEnemyColor()` → `ProceduralSprites.Get()`), the old private method stays behind with zero callers. It compiles silently but clutters the codebase.
**Fix**: After replacing a feature, `search_files` for the old method name across the project. If only definition remains (no callers), delete the method.

## Duplicate CI Runs Per Push

**Symptom**: Every `git push` creates TWO workflow runs (e.g. `29888399313` + `29888399304`) at the exact same timestamp. Both run on the same branch and commit. Sometimes one passes QG while the Build matrix fails in the other, creating confusing partial-green results.

**Root cause**: The workflow triggers on both `push` and `pull_request` events. A push to a branch that has an open PR triggers both events simultaneously:
```yaml
on:
  push:
    branches: [main, v1.1-dev]
  pull_request:
    branches: [main]   # pushes to v1.1-dev with open PR → fires both
```

**Fix**: 
- Option A: Remove `pull_request` trigger if PRs don't need separate CI
- Option B: Use `push` only for build, `pull_request` only for QG
- Option C: Add `if: github.event_name != 'pull_request'` guards on expensive jobs

**Diagnosis**:
```bash
gh run list --repo wuhoo-ai/miners-watch --limit 4 --json databaseId,createdAt,event,headBranch \
  -q '.[] | "\(.databaseId) \(.createdAt) \(.event) \(.headBranch)"'
```
If consecutive runs have identical timestamps → duplicate push+PR trigger.

## GameRoot → Additively-Loaded Scene Dependencies (FindObjectOfType Race)

**Symptom**: A system on the persistent `GameRoot` GameObject (created at app start, `DontDestroyOnLoad`) calls `FindObjectOfType<T>()` in `Awake()` to locate a component, but returns `null` because the target object lives in a scene that hasn't loaded yet (loaded additively later).

**Pattern**: GameRoot creates systems at `[RuntimeInitializeOnLoadMethod(BeforeSceneLoad)]`. These systems run `Awake()` before any additively-loaded game scenes. Components that live in `Surface.unity` or cave scenes are invisible to `FindObjectOfType` at that point.

**Example (2026-07-22)**: `DayNightPostProcess` on GameRoot needs a `Volume` component. The Volume lives in `Surface.unity` (loaded additively when player clicks "New Game"). `Awake()` → `FindObjectOfType<Volume>()` → `null`. Without a lazy retry, the system silently does nothing.

**Fix**: Use lazy discovery in `Update()` with a null-guard retry loop:
```csharp
private void Update()
{
    if (_targetComponent == null)
    {
        _targetComponent = FindObjectOfType<TargetType>();
        if (_targetComponent == null) return; // try again next frame
        // ... one-time init after discovery
    }
    // ... normal per-frame logic
}
```

**Prevention**: Any GameRoot system that references scene-local objects should either:
1. Use lazy discovery (as above), OR
2. Accept a `SetXxx()` public method that SceneAuthor calls after scene load, OR
3. Use `SceneManager.sceneLoaded` event to re-scan after additive loads

See `DayNightPostProcess.cs` for a reference implementation of pattern (1).

## Stale Scenes After SceneKit Changes (Runtime Features Missing)

**Symptom**: Code compiles ✅, CI builds ✅, QG green ✅, game launches, but runtime features are **missing** — buttons not appearing, UI misplaced, new components absent. ALL features from a version bump appear broken simultaneously. User says "新功能都没有生效" despite CI passing.

**Root cause**: Scene `.unity` files are static snapshots authored by Editor menu scripts (`SurfaceSceneAuthor`, `CaveSceneAuthor`). These scripts are **manual `[MenuItem]` actions**, NOT automatic build callbacks. When `SceneKit.cs` is modified (e.g., adding `AttackButton` to `BuildTouchControls`), the scene files on disk do NOT auto-update. The C# code advances but the `.unity` files stay frozen at their last author date.

**Key architecture insight**: `MainMenuBuilder` IS an automatic build callback (`IProcessSceneWithReport`), so MainMenu always stays fresh. But `SurfaceSceneAuthor` / `CaveSceneAuthor` are NOT — they require manual invocation.

**Diagnosis**:
```bash
# Compare last-author dates of scene files vs SceneKit/SceneAuthor changes
git log --oneline -1 -- Assets/Scenes/Surface.unity
git log --oneline -- Assets/Editor/SceneAuthoring/SceneKit.cs
# If SceneKit.cs was modified AFTER the last scene author commit → scenes are stale

# Verify a specific component is missing from the scene
grep -c "AttackBtn" Assets/Scenes/Surface.unity  # returns 0 = missing
```

**Fix**: Re-author ALL scenes from Unity Editor after any `SceneKit.cs` or `*SceneAuthor.cs` change:
- `Hermes → Author Surface Scene`
- `Hermes → Author Shallow Cave Scene`
- `Hermes → Author Mid Cave Scene`
- `Hermes → Author Deep Cave Scene`

Commit and push the regenerated `.unity` files, then rebuild.

**Prevention**: When implementing a task that modifies `SceneKit.cs` or any `*SceneAuthor.cs`, the task plan MUST include a final step: "Re-author all scenes + commit regenerated .unity files". The `wuhoo-game-dev-code-from-task` and `wuhoo-game-dev-review-task` skills should enforce this.

**Real case (2026-07-22)**: v1.2 features (AttackButton, enemies, combat) committed at `45adbdb`, SceneKit.cs updated to include AttackBtn in `BuildTouchControls`. But Surface.unity was last authored at `ebccb02` (2 days earlier, W8+W9). No scene re-author after v1.2 → 0 occurrences of "AttackBtn" in the scene → user reports ALL v1.2 features non-functional.

See also: `references/miners-watch-scene-architecture.md` for full architecture breakdown.

## WaveManager Deep Cave Boss Wave Unreachable (Index Gap)

**Symptom**: Guardian boss never spawns in Deep cave despite being configured.
**Root cause**: `_wavesPerNight=3` means only waveIndex 0/1/2 are used, but Guardian was at index 3/4 in the switch expression — dead branches.
**Fix**: (1) Make indices contiguous (0/1/2/3). (2) Set `_wavesPerNight` per depth in `Init()`:
```csharp
_wavesPerNight = depth == DepthLevel.Deep ? 4 : 3;
```
**Prevention**: When adding wave configs, verify index < `_wavesPerNight`. Add EditMode test asserting `AllWavesComplete` after expected wave count per depth.

## DayNightPostProcess NRE on Missing Volume Components

**Symptom**: `NullReferenceException` at `DayNightPostProcess.Update()` when entering a scene.
**Root cause**: `VolumeProfile.TryGet<T>(out T)` returns false when the profile lacks that component, leaving the out variable null. `Update()` accessed `_colorAdjustments.colorFilter` without null-check.
**Fix**: Guard every TryGet result before use: `if (_colorAdjustments != null && _colorAdjustments.colorFilter.overrideState)`.
**Prevention**: All `TryGet<T>()` results must be null-checked before property access.

## DamagePopup Font Allocation Leak

**Symptom**: Memory grows with frequent damage popups; Editor shows many Font objects.
**Root cause**: `Font.CreateDynamicFontFromOSFont()` allocates a new Font instance per call.
**Fix**: Cache in a `static Font _cachedFont` field, create once on first use.
**Prevention**: Runtime-created resources (Font, Material, Texture) should always be cached and reused.

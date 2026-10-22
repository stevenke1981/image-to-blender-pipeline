# 步態動畫 v0.1.0

## 範圍與執行狀態

保留原有圖片 → 3D → Blender 整理流程，追加獨立動畫階段。輸入必須先完成綁骨與權重；本階段不負責自動 Retopology、Rigging、Weight Painting。

2026-10-23（臺灣）：Python 數學層與負向驗證測試通過；本環境找不到 Blender executable，原生 Action、`.blend`、實際骨架求值與 PNG 渲染全部 **NOT_RUN**。`examples/gait/planned/` 是數學軌跡、CSV 與 SVG 曲線預覽，不是 Blender 動畫驗收證據。`references/gait/native-status/blender-status.json` 記錄缺少執行環境。不得將這份狀態改標為 PASS。

## 資料契約

使用 `schemas/gait.schema.json`（JSON Schema Draft 2020-12）。`core.validate()` 同時檢查跨欄位關係；內建 schema validator 僅實作此檔使用的詞彙，不能當成通用 JSON Schema 引擎。可另用 `jsonschema` 驗證 schema。

| 欄位 | 定義與單位 |
|---|---|
| type | biped、quadruped；serpentine 保留，產生器明確拒絕 |
| profile | age_years、maturity_years（物種成熟年齡）、neutral/tired/energetic |
| body | 腿長、軀幹長、左右髖寬（m），大腿佔腿長比例 |
| speed_mps | 世界 +Y 移動速度，m/s |
| step_length_m / stride_m | 一對交替腳步的一步 / 同腳再次落地的一完整跨步；stride = 2 × step |
| cadence_steps_per_s | 每秒交替步數；四足也以左右步對定義，不是四腳落地次數總和 |
| cycle_s | 完整循環秒數；cycle × cadence = 2；speed × cycle = stride |
| stance_fraction / stance_duration_s | 每隻腳接地比例 / 每週期接地秒數 |
| phase_offsets | 各肢相位 [0,1)；二足左右差半週期，四足預設四拍 walk |
| foot_clearance_m | 抬腳高度，m |
| pelvis_rotation_rad | XYZ 骨盆旋轉振幅，rad |
| com_displacement_m | XYZ 身體中心週期位移振幅，m；是骨盆中心代理，非質量積分的真實 COM |
| joint_limits_rad | hip/knee/ankle 的角度上下限，rad；實際關節角度寫入動畫資料 |
| snake_wave | 蛇類振幅、波長、頻率的預留介面，本版不產生蛇類 Action |

`schemas/gait-animation.schema.json` 定義實際動畫資料的關節角度與矩陣契約。`animation-data.json` 每筆包含時間、root、com、pelvis_rotation_rad、feet（世界腳點、stance、joint_angles_rad、ground_probe_z_m），以及實際求值的 bone_matrices、pelvis_matrix。髖角為大腿相對向下方向的前後傾角；膝角為從伸直算起的屈曲角；踝角用來保持腳掌朝向。不是解剖學多軸角度；骨盆旋轉依 XYZ Euler，骨架通道採 Quaternion。

GPT 可以提出參數，但必須通過 schema 與物理一致性檢查；不會把互相矛盾的步頻、速度靜默套入。預設 profile 是可編輯的藝術啟發式，非生物力學、醫療或物種實測資料。年齡使用相對成熟年齡；同齡不同物種不共用人類年齡分類。

## 無 Blender：產生與檢查資料

從 repository 根目錄執行（Python 3.10+，CLI 無第三方依賴）：

```bash
python scripts/gait_cli.py plan --type biped --age-years 75 --maturity-years 18 --state tired --leg-length-m 0.9 --upper-leg-ratio 0.5 --speed-mps 0.35 --out gait-output/elder.json
python scripts/gait_cli.py inspect --config gait-output/elder.json --out gait-output/elder-planned
python -m unittest discover -s tests -v
```

可選：`python -m pip install jsonschema`，讓測試同時使用獨立 Draft 2020-12 實作；沒安裝會清楚標 SKIP。三組固定測試輸入為 `biped_adult.json`、`biped_elder_tired.json`、`quadruped_walk.json`。

## Blender：測試骨架、Action 與預覽

目標 Blender 4.2+；目前未做任何版本原生相容性聲明。腳本使用 keyframe_insert，並區分 legacy 與 layered Action F-Curve 讀取，避免依賴已移除的舊版 Action API。

```bash
python scripts/check_blender_gaits.py --blender blender --out gait-output
```

Windows 可用 `--blender "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"`。Runner 依次執行三組，不使用 GitHub Actions 分鐘；沒有 executable 以 exit 2 / NOT_RUN 結束。原生例外、驗證不通過或缺少檔案以非零結束，Blender 呼叫使用 `--python-exit-code 1`。

單組：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/blender_gait.py -- --config examples/gait/biped_adult.json --out gait-output/adult
```

每組輸出：`animation.blend`（Action 名稱等於 config.name）、`animation-data.json`、`rig-map.json`、`validation.json`、三張不同相位 `preview-1.png` 至 `preview-3.png`。測試骨架附帶骨段 mesh 代理，讓渲染不是空畫面。`--skip-render` 僅驗證動畫，不代表視覺驗收通過。

完整循環烘焙至 N+1 key（含閉合姿態），播放範圍 1..N，避免重複端點停頓。root 每循環前進 stride_m，重複使用時需以 root motion 累加位置，或在 NLA 使用相應偏移；直接重複絕對位置會跳回原點。本版不自動建立 NLA 重複。

## 接現有角色

```bash
blender --background --python-exit-code 1 --python scripts/blender_gait.py -- --config examples/gait/biped_adult.json --input character.blend --rig-map examples/gait/biped.rig.json --out gait-output/character
```

只寫到新的輸出 `.blend`。先複製 rig 並套用物件 transforms，位於世界原點，+Y 前、+Z 上，單位 m。用 mapping 指定 armature、pelvis、每肢 upper/lower/foot 名稱、bend_sign、sole_offset 與 ground_probes。範例 mapping 可改成角色自己的骨名；`sole_offset` 與 `ground_probes` 都是 foot bone-local metres，後者至少涵蓋腳跟與腳尖。測試骨架的 foot local +Y 沿腳掌長度。

支援 pelvis > upper > lower > foot 的直接雙節變形骨鏈；父子關節位置必須重合，不強制 Blender use_connect。拒絕映射骨上的 constraints、物件 constraints/drivers、NLA、重複角色或缺骨。先另行 bake/prepare 複雜 control rig；本版不直接接 Rigify/Mixamo 控制器或多節趾行腿。讀入 config 必須符合實際髖寬、前後髖間距、上下腿比例，映射不會自動把不合比例的動作硬套上去。foot rest orientation 決定固定腳掌方向，須準備平放的 rest pose。

鼠、牛、虎、兔、恐龍、馬、羊、猴、雞、狗、豬的人型版先走 biped；動物版依實際骨架選 biped（例如雞、二足恐龍）或 quadruped（例如牛、虎、狗）。蛇的動物版保留 serpentine；蛇的人型版若有雙腿可用 biped。此流程共用資料契約，不代表所有物種已具備專門步法。跑、跳、兔躍、馬步態切換、尾巴/手臂/頭部 secondary motion、地形適應尚未實作。

## 驗證與待驗

Python 層驗證固定接地世界座標、累積接地漂移、地面高度、循環位置與邊界速度；包含故意滑腳、穿地、接縫錯位與速度突變的負向案例。IK 超出可達範圍或關節限制會失敗，不用骨長伸縮掩蓋。

Blender 層以 evaluated depsgraph 讀取 foot sole 點、腳跟/腳尖 probes、所有骨頭矩陣，再檢查滑腳、穿地、局部姿態閉合。每幀取八個子樣本並線性烘焙；位置/漂移容許 2 mm，腳部循環邊界速度誤差容許 0.25 m/s，骨矩陣閉合容許 1e-4。這是測試骨架的工程門檻；小型角色應縮小容許值。地面檢查針對指定 probes，不能代替整個 mesh 碰撞檢查。

待在 Blender 實際執行後確認：

- 三組產生非空 Action、可重開 `.blend`、完整動畫 JSON 與三張 PNG。
- 原生 validation.json 全為 PASS，重新開檔播放 1..N 檢查循環與膝彎方向。
- 另用重新命名的骨架與不同身體比例測試 mapping，確認腳底 offsets。
- 檢查權重、皮膚變形、全 mesh 穿地與自然度；骨架數學通過不能代替角色視覺驗收。
- 驗證 Blender 4.2 與較新 layered Actions 版本；本環境皆 NOT_RUN。

API 參考：https://docs.blender.org/api/4.2/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert ；https://developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/

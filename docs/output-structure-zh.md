# Output 結構說明

這份文件說明 `output/` 目錄目前會產生哪些資料、圖表，以及它們各自代表的分析意義。

## 1. 總覽

`output/` 目前分成兩大區塊：

- `output/coverage/`：著重在 coverage 本身的成長與策略之間的比較。
- `output/analysis/`：著重在固定 path 預算下的橫向比較，以及 coverage 與 path 複雜度之間的 trade-off。

整體結構如下：

```text
output/
  coverage/
    strategies/
      <strategy>/
        <project>/
          <project>_sorted_paths.json
          <project>_coverage_summary.json
          <project>_state_coverage.png
          <project>_transition_coverage.png
          <project>_state_coverage_ratio.png
          <project>_transition_coverage_ratio.png
    comparison/
      <project>/
        <project>_strategy_state_coverage.png
        <project>_strategy_transition_coverage.png
        <project>_strategy_state_coverage_ratio.png
        <project>_strategy_transition_coverage_ratio.png
      average/
        average_strategy_state_coverage.png
        average_strategy_transition_coverage.png
        average_strategy_state_coverage_ratio.png
        average_strategy_transition_coverage_ratio.png
        summary.json
      strategy_score_summary.json
      strategy_score_cumulative.png
  analysis/
    path_count_compare/
      paths-5/
      paths-10/
      paths-15/
      paths-20/
      paths-25/
      paths-30/
    path_scatter/
      comparison/
        paths-5/
        paths-10/
        ...
      <project>/
        paths-5/
        paths-10/
        ...
```

## 2. 四種核心指標

所有圖表基本上都圍繞以下四種 coverage 指標：

- `state_coverage`：已覆蓋的 state 數量。
- `state_coverage_ratio`：已覆蓋 state / 全部 state，值介於 0 到 1。
- `transition_coverage`：已覆蓋的 transition 數量。
- `transition_coverage_ratio`：已覆蓋 transition / 全部 transition，值介於 0 到 1。

如果你想看「絕對覆蓋量」，優先看 `state_coverage`、`transition_coverage`；如果你想比較不同 project 的相對達成度，優先看 ratio 版本。

## 3. output/coverage/

### 3.1 `output/coverage/strategies/<strategy>/<project>/`

這一層是「單一策略、單一 project」的原始分析結果，最適合回答這類問題：

- 某一個策略在某個 project 上，隨著 path 數量增加，coverage 是怎麼成長的？
- 排序後的 path 順序是什麼？

常見檔案如下：

#### `<project>_sorted_paths.json`

這是排序後的 path 清單。它保留每條 path 的：

- 排序後順位 `sortedIndex`
- 原始順序 `originalSequence`
- 來源檔案 `sourceFile`
- path 名稱 `name`
- 語意目標 `semanticGoal`
- 邊集合 `edgeIds`
- path 長度 `pathLength`

用途是回答：「工具最後選出來的 path 順序是什麼？哪一條 path 對 coverage 增益較前面？」

#### `<project>_coverage_summary.json`

這是 coverage 成長的結構化摘要，主要包含：

- graph 的總 state 數與總 transition 數
- 每個 `pathCount` 下的 `coveredStates`
- 每個 `pathCount` 下的 `coveredTransitions`
- 對應的 coverage ratio

用途是讓你不看圖，也可以直接讀取每增加一條 path 後的 coverage 變化。

#### 四張單策略折線圖

- `<project>_state_coverage.png`
- `<project>_transition_coverage.png`
- `<project>_state_coverage_ratio.png`
- `<project>_transition_coverage_ratio.png`

這四張圖的 X 軸都是 path count，Y 軸是對應的 coverage 指標。

解讀方式：

- 曲線上升越快，代表前幾條 path 就能帶來較大的 coverage 增益。
- 曲線越早接近飽和，代表這個策略比較早達到 coverage 上限。

### 3.2 `output/coverage/comparison/<project>/`

這一層是「同一個 project，不同策略」的比較圖，最適合回答：

- 在同一個 project 上，哪個策略 coverage 成長比較快？
- 哪個策略較早達成完整 coverage？

每個 project 會有四張對照折線圖：

- `<project>_strategy_state_coverage.png`
- `<project>_strategy_transition_coverage.png`
- `<project>_strategy_state_coverage_ratio.png`
- `<project>_strategy_transition_coverage_ratio.png`

這些圖把多個 strategy 疊在同一張圖上，讓你直接比較不同策略在同一 project 上的 coverage 成長曲線。

### 3.3 `output/coverage/comparison/average/`

這一層是把所有 project 做平均後的策略比較，最適合回答：

- 如果從整體來看，而不是只看單一 project，哪個策略平均表現較好？

內容包含：

- `average_strategy_state_coverage.png`
- `average_strategy_transition_coverage.png`
- `average_strategy_state_coverage_ratio.png`
- `average_strategy_transition_coverage_ratio.png`
- `summary.json`

圖的 X 軸仍然是 path count，Y 軸則是跨所有 project 的平均 coverage 值。

`summary.json` 會補充：

- 納入平均的 project 名單
- 每個策略在每個 path count 下的平均值
- 每個 project 實際使用了幾條 path

這份 JSON 很適合後續做表格整理、論文數據引用或其他二次分析。

### 3.4 `strategy_score_summary.json`

這份檔案是整體策略評分摘要，用來把每個 project、每個 metric 的比較結果整合成一份總分表。

目前的評分邏輯是：

- 如果某策略能達到某個 metric 的完整 coverage，越早用更少 path 達成，排名越前。
- 如果沒有達到完整 coverage，則以最後能達到的 coverage 值來比較，越高越好。
- 每個 metric 會轉成一個名次分數，再累積成 project 分數與總分。

因此這份 JSON 適合回答：

- 綜合四個 coverage 指標後，哪個策略整體最強？
- 某個策略是靠哪些 project 拉高總分？

主要欄位包括：

- `strategyScores`：每個策略的總分
- `projectScoresByStrategy`：每個策略在每個 project 的分數
- `cumulativeScoresByStrategy`：每個策略依 project 累積的分數
- `projects`：每個 project 內，四個 metric 的細部分數與 ranking

### 3.5 `strategy_score_cumulative.png`

這張圖把 `cumulativeScoresByStrategy` 視覺化。X 軸是 project，Y 軸是累積分數。

適合觀察：

- 哪些策略一路穩定領先
- 哪些策略在某些 project 開始明顯拉開差距

## 4. output/analysis/

### 4.1 `output/analysis/path_count_compare/paths-N/`

這一層的觀點是「固定 path 預算」下的平均 coverage 比較。

例如 `paths-5/` 代表：

- 每個 strategy/project 最多只看前 5 條排序後 path
- 然後比較各策略在這個固定 path 數量下的平均 coverage

每個 `paths-N/` 目錄包含：

- `state_coverage.png`
- `transition_coverage.png`
- `state_coverage_ratio.png`
- `transition_coverage_ratio.png`
- `summary.json`

這四張圖是長條圖，X 軸通常是 strategy，Y 軸是跨所有 project 的平均 coverage 值。

最適合回答：

- 如果 path 預算只有 5 條、10 條、15 條，哪個策略最值得選？
- 在固定 path 數量下，coverage 表現差距有多大？

`summary.json` 會列出：

- path limit
- project 名單
- 每個指標下各策略的平均值
- 各 project 對應的實際值與實際 path 數

### 4.2 `output/analysis/path_scatter/comparison/paths-N/`

這一層是「跨所有 project 平均後」的散點 trade-off 分析。

每個 `paths-N/` 底下會有：

- `state_coverage_vs_average_path_length.png`
- `transition_coverage_vs_average_path_length.png`
- `state_coverage_ratio_vs_average_path_length.png`
- `transition_coverage_ratio_vs_average_path_length.png`
- 上述四張各自對應的 `_pareto_frontier.png`
- `summary.json`

這些圖的共同定義是：

- X 軸：某種 coverage 指標的平均值
- Y 軸：平均 path length
- 每個點：一個 strategy

它們要回答的不是「coverage 單獨最高的是誰」，而是：

- 在想提高 coverage 的同時，能不能讓平均 path 長度維持更短？

也就是說，這一組圖在看 coverage 與 path 複雜度之間的 trade-off。

#### `_pareto_frontier.png` 的意思

Pareto 版本和原始散點圖資料完全相同，只是額外把「被支配」的策略淡化並打叉。

這裡的支配關係定義為：

- coverage 不比別人高
- 平均 path length 不比別人短
- 且至少有一項更差

因此在 Pareto 圖中保留下來的亮點，代表的是在「coverage 越高越好、path 越短越好」前提下仍然值得考慮的策略。

### 4.3 `output/analysis/path_scatter/<project>/paths-N/`

這一層和上一節很像，但不做跨 project 平均，而是直接看「單一 project」內的 trade-off。

每個 project 底下都會再切成多個 `paths-N/`，例如：

- `output/analysis/path_scatter/1-1/paths-5/`
- `output/analysis/path_scatter/1-1/paths-10/`

每個資料夾包含：

- 四張 coverage vs average path length 散點圖
- 四張對應的 Pareto frontier 強調版
- `summary.json`

這一層最適合回答：

- 對某個特定 project 而言，在固定 path 數量下，哪個策略是最佳折衷？
- 某些策略雖然 coverage 很高，但是否帶來過長、過複雜的 path？

如果你要寫案例分析或展示單一 graph 的策略選擇，這一層通常最有用。

## 5. summary.json 可以怎麼用

各目錄下的 `summary.json` 主要是給機器讀取或後續分析使用。實務上你可以把它當成：

- 論文或報告中表格的原始資料來源
- 再次繪圖的輸入
- 自動化比較策略結果的中介格式

幾個常見用途如下：

- 想做自己的 Excel 表格：讀 `summary.json` 即可，不必從圖片人工抄數字。
- 想比對特定 strategy 在不同 project 的表現：優先看 `coverage/comparison/average/summary.json` 或 `path_count_compare/paths-N/summary.json`。
- 想分析 coverage 與 path length 的取捨：優先看 `path_scatter/.../summary.json`。

## 6. 補充說明

### 6.1 `--max-paths-per-project` 的影響

執行時如果指定 `--max-paths-per-project N`，所有圖表與摘要都只會使用每個 strategy/project 排序後的前 `N` 條 path。

這樣做的目的是讓不同策略之間的比較更公平，因為原始 path 數量可能不一致。

### 6.2 固定 path 數量是上限，不是最低門檻

像 `paths-5`、`paths-10` 這些資料夾中的數字，代表的是「最多使用 N 條 path」的 cap。

如果某個 strategy/project 本身沒有那麼多 path，系統會：

- 使用它最後一個可用的 coverage snapshot
- average path length 也以實際可用 path 數量計算

因此在讀 `actualPathCountUsed` 或 `actualPathCounts` 這些欄位時，要注意它們不一定總是等於資料夾名稱中的 `N`。

## 7. 建議閱讀順序

如果你是第一次看這份 output，建議依序閱讀：

1. `output/coverage/strategies/...`：先理解單一策略在單一 project 上的 coverage 成長。
2. `output/coverage/comparison/<project>/...`：再看同一個 project 內不同策略的比較。
3. `output/analysis/path_count_compare/paths-N/...`：看固定 path 預算下誰的平均 coverage 最好。
4. `output/analysis/path_scatter/.../_pareto_frontier.png`：最後看 coverage 與 path 複雜度的最佳折衷解。

如果你的目標是直接做策略選擇，通常可以優先看：

- `path_count_compare/paths-N/`：回答「固定 path 預算時選誰」
- `path_scatter/.../_pareto_frontier.png`：回答「在 coverage 與 path length 之間，哪些策略根本不值得考慮」
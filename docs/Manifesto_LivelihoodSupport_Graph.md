# Manifesto: Livelihood Protection Support & Dignity Graph
# 生活保護受給者の尊厳支援マニフェスト

**Version:** 1.4
**Last Updated:** 2025-12-28

---

## 0. 理念 (Philosophy)

我々が構築するのは、単なる「生活保護受給者の管理台帳」ではない。

生活保護制度は、日本国憲法第25条が保障する「健康で文化的な最低限度の生活を営む権利」を具現化するための制度である。しかし、現場では膨大な書類業務に追われ、本来最も大切にすべき**「その人を理解する」**という営みが後回しにされている。

### 生活保護支援の現実

- 保護申請時の聴き取りは、本人の記憶があいまいだったり、話したくない過去があったりして、**不正確・不十分であることが多い**
- 生活歴や保護に至った経緯は、あくまで「本人の語り」であり、客観的事実とは限らない
- 家族関係が断絶しているケースも多く、本人以外から情報を得ることが難しい
- **判断能力の低下により金銭管理が困難なケースや、親族からの経済的搾取を受けているケースも少なくない**

**だからこそ、ケースワーカーが日々作成する「ケース記録」が最も重要な一次資料となる。**

ケース記録は、支援者の目を通して観察された事実であり、時間をかけて積み重ねられることで、徐々に本人の全体像が浮かび上がってくる。このナレッジグラフは、**ケース記録の蓄積を通じて、一人の人間を立体的に理解していくプロセス**を支援するためのものである。

### 見落とされがちな危険：支援者による二次被害

生活保護受給者、特に比較的若い世代には、**うつ病、統合失調症、発達障害などの精神疾患**を抱えている方が少なくない。彼らの多くは：

- 人との接触そのものが困難である
- 就労への意欲を持つこと自体が病状により難しい
- 社会との接点を持つこと自体が大きなストレスとなる

このような状態にある人に対して、ケースワーカーが**「なぜ働かないのか」「いつまでも甘えていてはいけない」**といった批判的な生活指導を行うことがある。

**しかし、その「指導」こそが、本人を二次的な障害に追い込む危険性がある。**

| 批判的指導がもたらすリスク |
|:---|
| 症状の悪化（うつの深刻化、統合失調症の再発） |
| 自己肯定感の喪失（「自分はダメな人間だ」という確信） |
| 支援拒否・引きこもりの深刻化（ケースワーカーを避ける） |
| 最悪の場合、自殺・自傷行為 |

**このデータベースは、支援者が「善意の加害者」にならないための防波堤でもある。**

### 7つの基本価値

1. **Dignity (尊厳):** 「受給者」という匿名の存在ではなく、固有の歴史と願いを持つ一人の人間として捉える。
2. **Do No Harm (害を与えない):** 支援者の関わり方が本人を傷つける可能性を常に意識する。
3. **Accumulation (蓄積):** ケース記録の積み重ねを通じて、徐々に本人理解を深めていく。
4. **Continuity (支援の継続性):** ケースワーカーが異動しても、蓄積された理解と支援の文脈を断絶させない。
5. **Empowerment (自立支援):** 「指導」ではなく「伴走」の姿勢で、本人の強みと可能性を発見していく。
6. **Connection (つながり):** 孤立しがちな受給者と社会資源を結びつけ、セーフティネットを構築する。
7. **Collaboration (多機関連携):** 複合的な課題には一人で抱え込まず、関係機関と連携して対応する。

---

## 1. なぜこのデータベースが必要か（Why This Database?）

### 1.1 ケース記録の価値を最大化する

| 現状の課題 | このデータベースが解決すること |
|:---|:---|
| ケース記録が紙やExcelに散在し、過去の記録を参照できない | すべての記録をグラフ構造で関連付け、時系列で追跡可能に |
| 担当者異動のたびに「一から観察し直し」が必要 | 蓄積されたケース記録から本人像を即座に把握可能 |
| 記録が「書いて終わり」になり、活用されない | 記録から自動的にパターンや傾向を抽出し、支援に活かす |
| 複合的な困難（精神疾患+DV+多重債務等）の関係性が見えない | 複数の課題間の関係性をグラフで可視化 |
| 過去に効果があった支援策が個人の記憶に埋もれる | 支援履歴と成果を蓄積し、エビデンスに基づく支援を可能に |
| **不適切な関わり方が本人を追い込んでいることに気づけない** | **逆効果だった対応を記録し、同じ過ちを繰り返さない** |
| **類似のケースでうまくいった支援策がわからない** | **類似案件パターンを蓄積し、効果的な介入を提案** |
| **多機関連携の経緯が記録されず、引き継げない** | **連携記録をグラフで管理し、関係機関との協働を可視化** |

### 1.2 ケース記録から本人像を構築するプロセス

```
【従来のアプローチ】
初回聴き取り → 生活歴作成 → （不正確なまま固定化）→ ケース記録（散在）

【本データベースのアプローチ】
初回聴き取り → 暫定的な情報として記録
    ↓
日々のケース記録の蓄積
    ↓
記録から浮かび上がるパターン・特性の抽出
    ↓
本人像の継続的なアップデート
    ↓
効果的だった関わり方・避けるべき関わり方の明確化
    ↓
類似案件との比較・効果的な介入策の発見
    ↓
より正確で立体的な本人理解へ
```

### 1.3 受給者にとってのメリット

- **「何度も同じことを聞かれる」ストレスからの解放**
- **時間をかけて理解してもらえる**（初回聴き取りだけで判断されない）
- **異動後の新担当者にも、これまでの経過が引き継がれる**
- **自分を傷つける対応から守られる**（避けるべき関わり方が継承される）
- **経済的搾取から守られる**（リスクが共有され、適切な支援につながる）

---

## 2. データモデルの7本柱 (The 7 Pillars)

### 第1の柱：ケース記録（最重要）(Case Records - Primary Source)
* **役割:** 支援者の観察に基づく一次資料。本人理解の土台となる。
* **主要ノード:** `:CaseRecord` (ケース記録), `:HomeVisit` (家庭訪問記録), `:Observation` (観察事項)
* **重要性:** ★★★★★（すべての柱の基盤）

### 第2の柱：抽出された本人像 (Extracted Profile)
* **役割:** ケース記録から抽出・蓄積された本人の特性や傾向。
* **主要ノード:** `:SupportPreference` (支援上の配慮), `:Strength` (強み), `:Challenge` (課題), `:Pattern` (行動パターン)
* **重要性:** ★★★★☆（記録から継続的に更新）

### 第3の柱：関わり方の知恵（効果と禁忌）(Approach Wisdom)
* **役割:** 「どう関わるべきか」「何をしてはいけないか」を定義する。
* **主要ノード:** `:EffectiveApproach` (効果的だった関わり方), `:NgApproach` (避けるべき関わり方), `:TriggerSituation` (注意が必要な状況)
* **重要性:** ★★★★★（二次被害防止の要）

### 第4の柱：参考情報としての申告歴 (Declared History - Reference)
* **役割:** 本人からの聴き取りに基づく情報。参考情報として位置づける。
* **主要ノード:** `:DeclaredHistory` (申告された生活歴), `:PathwayToProtection` (保護に至った経緯), `:Wish` (本人の願い)
* **重要性:** ★★★☆☆（不正確な可能性を前提に参照）

### 第5の柱：社会的ネットワーク (Social Safety Net)
* **役割:** 「誰とつながっているか」を定義する。
* **主要ノード:** `:KeyPerson` (キーパーソン), `:FamilyMember` (家族), `:SupportOrganization` (支援機関)
* **重要性:** ★★★★☆

### 第6の柱：法的・制度的基盤 (Legal & Institutional Basis)
* **役割:** 「どんな権利・支援を受けているか」を定義する。
* **主要ノード:** `:ProtectionDecision` (保護決定), `:Certificate` (各種手帳), `:SupportGoal` (支援目標)
* **重要性:** ★★★☆☆

### 第7の柱：金銭的安全と多機関連携 (Financial Safety & Multi-Agency Collaboration) 【Version 1.4 新設】
* **役割:** 金銭管理困難や経済的虐待への対応、多機関連携の記録と類似案件の知見蓄積
* **主要ノード:** `:MoneyManagementStatus` (金銭管理状況), `:EconomicRisk` (経済的リスク), `:DailyLifeSupportService` (日常生活自立支援事業), `:CollaborationRecord` (連携記録), `:CasePattern` (類似案件パターン)
* **重要性:** ★★★★★（経済的安全の確保と連携知見の蓄積）

---

## 3. スキーマ定義 (Schema Definition)

### 3.1 ケース記録（最重要）(Case Records - Primary Source)

**ケース記録は、このデータベースの心臓部である。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:CaseRecord** | `date`, `category`, `content`, `caseworker`, `source`, `recipientResponse` | 日々のケース記録。本人の反応も記録。 |
| **:HomeVisit** | `date`, `observations`, `recipientCondition`, `livingEnvironment`, `recipientMood`, `nextAction` | 家庭訪問の詳細記録。本人の様子も含む。 |
| **:Observation** | `date`, `type`, `content`, `reliability` | 特定の観察事項。記録から抽出された事実。 |
| **:Interaction** | `date`, `type` (電話/来所/同行), `summary`, `recipientResponse`, `approachUsed` | 本人とのやり取り。どんな関わり方をしたかも記録。 |

* **リレーション:**
    * `(:Recipient)-[:HAS_RECORD]->(:CaseRecord)`
    * `(:CaseRecord)-[:OBSERVED]->(:Observation)`
    * `(:CaseRecord)-[:SUGGESTS]->(:Pattern)`
    * `(:CaseRecord)-[:REVEALS]->(:Strength)`
    * `(:CaseRecord)-[:IDENTIFIES]->(:Challenge)`
    * `(:CaseRecord)-[:USED_APPROACH]->(:EffectiveApproach)`
    * `(:CaseRecord)-[:TRIGGERED_BY]->(:NgApproach)`
    * `(:CaseRecord)-[:LED_TO]->(:CollaborationRecord)` 【新規】

### 3.2 抽出された本人像 (Extracted Profile)

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:SupportPreference** | `category`, `instruction`, `reason`, `sourceRecords[]`, `confidence` | 効果的な関わり方。根拠となる記録IDを紐付け。 |
| **:Strength** | `description`, `discoveredDate`, `sourceRecords[]`, `context` | 記録から発見された強み。 |
| **:Challenge** | `description`, `severity`, `firstIdentified`, `currentStatus`, `sourceRecords[]` | 課題。初認識日と現在の状態を管理。 |
| **:Pattern** | `description`, `frequency`, `triggers`, `sourceRecords[]` | 行動パターン。 |
| **:MentalHealthStatus** | `diagnosis`, `currentStatus`, `symptoms`, `treatmentStatus`, `lastAssessment` | 精神疾患の状況。支援方針に直結。 |

* **リレーション:**
    * `(:Recipient)-[:HAS_CONDITION]->(:MentalHealthStatus)`
    * `(:MentalHealthStatus)-[:REQUIRES]->(:EffectiveApproach)`
    * `(:MentalHealthStatus)-[:CONTRAINDICATED]->(:NgApproach)`

### 3.3 関わり方の知恵（効果と禁忌）(Approach Wisdom)

**支援者が「善意の加害者」にならないための最重要スキーマ。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:EffectiveApproach** | `description`, `context`, `sourceRecords[]`, `frequency` | 効果があった関わり方。どんな状況で効果的だったかも記録。 |
| **:NgApproach** | `description`, `reason`, `riskLevel`, `consequence`, `sourceRecords[]` | **絶対に避けるべき関わり方。** 過去に本人を傷つけた対応。 |
| **:TriggerSituation** | `description`, `signs`, `recommendedResponse` | 注意が必要な状況。このサインが見えたらこう対応する。 |
| **:CriticalIncident** | `date`, `description`, `trigger`, `outcome`, `lessonsLearned` | 重大なインシデント（症状悪化、自傷など）。再発防止のための記録。 |

* **リレーション:**
    * `(:Recipient)-[:RESPONDS_WELL_TO]->(:EffectiveApproach)`
    * `(:Recipient)-[:MUST_AVOID]->(:NgApproach)`
    * `(:Recipient)-[:HAS_TRIGGER]->(:TriggerSituation)`
    * `(:NgApproach)-[:CAUSED]->(:CriticalIncident)`
    * `(:TriggerSituation)-[:PREVENTED_BY]->(:EffectiveApproach)`

#### 3.3.1 NgApproach（避けるべき関わり方）の具体例

| カテゴリ | 例 | リスク |
|:---|:---|:---|
| **批判的指導** | 「なぜ働かないのか」「甘えている」 | うつ悪化、自己否定感の深刻化 |
| **性急な就労圧力** | 「いつまでに就職するのか」 | パニック、引きこもり悪化 |
| **約束の強要** | 「次回までに○○すると約束してください」 | プレッシャーによる症状悪化 |
| **比較** | 「他の人はできているのに」 | 自己肯定感の喪失 |
| **予告なし訪問** | 突然の家庭訪問 | 不安の増大、信頼関係の破壊 |
| **長時間の面談** | 1時間を超える来所面談 | 疲労による症状悪化 |
| **詰問調の質問** | 「本当ですか？」「証拠は？」 | 被害妄想の誘発、信頼喪失 |

### 3.4 参考情報としての申告歴 (Declared History - Reference)

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:Recipient** | `caseNumber`, `name`, `dob`, `gender`, `address`, `protectionStartDate` | 受給者本人の基本情報。 |
| **:DeclaredHistory** | `era`, `content`, `declaredDate`, `reliability`, `corroboratingRecords[]` | 本人が申告した生活歴。 |
| **:PathwayToProtection** | `declaredTrigger`, `declaredTimeline`, `reliability`, `caseRecordNotes` | 本人が語った保護に至った経緯。 |
| **:Wish** | `content`, `priority`, `declaredDate`, `status`, `actionsTaken[]` | 本人の願い。 |

* **リレーション:**
    * `(:DeclaredHistory)-[:CORROBORATED_BY]->(:CaseRecord)`
    * `(:DeclaredHistory)-[:CONTRADICTED_BY]->(:CaseRecord)`

### 3.5 社会的ネットワーク (Social Safety Net)

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:KeyPerson** | `name`, `relationship`, `contactInfo`, `rank`, `role`, `lastContact` | 緊急連絡先。 |
| **:FamilyMember** | `name`, `relationship`, `contactStatus`, `supportCapacity`, `lastInteraction`, `riskFlag` | 家族構成。経済的リスクがある場合はフラグを立てる。 |
| **:SupportOrganization** | `name`, `type`, `contactPerson`, `services`, `utilizationStatus` | 支援機関。 |
| **:MedicalInstitution** | `name`, `department`, `doctor`, `visitFrequency`, `role` | 医療機関。精神科の主治医は特に重要。 |

### 3.6 法的・制度的基盤と支援計画 (Legal Basis & Support Plan)

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:ProtectionDecision** | `decisionDate`, `type`, `protectionCategory`, `monthlyAmount` | 保護の決定内容。 |
| **:Certificate** | `type`, `grade`, `expiryDate` | 各種証明書・手帳。 |
| **:SupportGoal** | `description`, `targetDate`, `status`, `basedOnRecords[]`, `paceConsideration` | 支援目標。本人のペースを考慮。 |

### 3.7 金銭的安全と多機関連携 (Financial Safety & Multi-Agency Collaboration) 【新設】

**判断能力の低下による金銭管理困難や、親族等からの経済的搾取は、生活保護受給者が直面する重大なリスクである。**

#### 3.7.1 金銭管理状況 (Money Management Status)

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:MoneyManagementStatus** | `capability`, `pattern`, `riskLevel`, `triggers[]`, `observations`, `assessmentDate` | 本人の金銭管理能力と課題 |

* **capability（管理能力）の分類:**
    * `自己管理可能` - 支援なしで管理できる
    * `支援があれば可能` - 声かけや確認があれば管理できる
    * `支援が必要` - 定期的な支援が必要
    * `困難` - 自己管理が著しく困難、支援サービスの導入を検討

* **pattern（パターン）の例:**
    * 「受給日から数日で使い果たす」
    * 「特定の支出（ギャンブル、通販等）で浪費する」
    * 「親族に渡してしまう」
    * 「詐欺に遭いやすい」

#### 3.7.2 経済的リスク (Economic Risk)

**家族や第三者による経済的虐待・搾取を記録する。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:EconomicRisk** | `type`, `perpetrator`, `perpetratorRelationship`, `severity`, `description`, `discoveredDate`, `status`, `interventions[]` | 経済的リスクの詳細 |

* **type（リスク種別）:**
    * `金銭搾取` - 親族等による金銭の搾取
    * `無心・たかり` - 繰り返しの金銭要求
    * `通帳管理強要` - 通帳・カードの管理を強要
    * `借金の肩代わり強要` - 本人に借金を負わせる
    * `年金・手当の横領` - 受給している年金等の横領
    * `住居費の搾取` - 家賃等を不当に徴収
    * `詐欺被害リスク` - 詐欺に遭いやすい状況
    * `浪費` - 本人自身による浪費

* **severity（深刻度）:**
    * `High` - 緊急対応が必要（保護費の大部分が搾取されている等）
    * `Medium` - 継続的な監視と介入が必要
    * `Low` - 注意を要するが現時点で緊急性は低い

* **status（状態）:**
    * `Active` - 現在も継続中
    * `Monitoring` - 介入済みだが監視継続
    * `Resolved` - 解決済み

#### 3.7.3 日常生活自立支援事業 (Daily Life Support Service)

**社会福祉協議会が提供する日常生活自立支援事業の利用状況を記録する。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:DailyLifeSupportService** | `socialWelfareCouncil`, `startDate`, `services[]`, `frequency`, `specialist`, `contactInfo`, `status`, `referralRoute`, `reason` | 日常生活自立支援事業の利用詳細 |

* **services（サービス内容）:**
    * `福祉サービス利用援助` - 福祉サービスの利用手続き支援
    * `日常的金銭管理サービス` - 預金の払い戻し、公共料金の支払い等
    * `書類等預かりサービス` - 通帳、年金証書等の預かり

* **referralRoute（紹介経路）:**
    * `地域包括支援センター経由`
    * `福祉事務所から直接`
    * `医療機関から紹介`
    * `その他`

#### 3.7.4 多機関連携記録 (Collaboration Record)

**ケース会議、情報共有、合同対応などの記録を残す。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:CollaborationRecord** | `date`, `type`, `participants[]`, `agenda`, `discussion`, `decisions[]`, `nextActions[]`, `createdBy` | 連携の詳細記録 |

* **type（連携種別）:**
    * `ケース会議` - 複数機関が参加する会議
    * `情報共有` - 電話やメールでの情報共有
    * `緊急対応` - 緊急事態への合同対応
    * `定期連絡` - 定期的な状況確認

* **participants（参加者）:**
    * 名前、所属機関、役割を記録

#### 3.7.5 類似案件パターン (Case Pattern)

**過去の類似案件から学んだ知見を蓄積し、新規案件に活用する。**

| ノードラベル | プロパティ例 | 説明 |
|:---|:---|:---|
| **:CasePattern** | `patternName`, `description`, `indicators[]`, `riskFactors[]`, `recommendedInterventions[]`, `successfulCases`, `relatedServices[]` | 類似案件パターンと効果的な介入 |

* **例：「親族による金銭搾取パターン」**
    * `indicators`: ["受給日直後に金銭がなくなる", "特定の親族との接触後に困窮", "本人が搾取を認めない"]
    * `riskFactors`: ["判断能力の低下", "親族への依存", "孤立"]
    * `recommendedInterventions`: ["日常生活自立支援事業の導入", "本人との信頼関係構築", "親族との接触機会の調整"]
    * `relatedServices`: ["日常生活自立支援事業", "成年後見制度"]

#### 3.7.6 リレーション

```
(:Recipient)-[:HAS_MONEY_STATUS]->(:MoneyManagementStatus)
(:Recipient)-[:FACES_RISK]->(:EconomicRisk)
(:FamilyMember)-[:POSES_RISK]->(:EconomicRisk)
(:Recipient)-[:USES_SERVICE]->(:DailyLifeSupportService)
(:DailyLifeSupportService)-[:PROVIDED_BY]->(:SupportOrganization)
(:EconomicRisk)-[:MITIGATED_BY]->(:DailyLifeSupportService)
(:CollaborationRecord)-[:ABOUT]->(:Recipient)
(:CollaborationRecord)-[:INVOLVED]->(:SupportOrganization)
(:CaseRecord)-[:LED_TO]->(:CollaborationRecord)
(:Recipient)-[:MATCHES_PATTERN]->(:CasePattern)
(:CasePattern)-[:RECOMMENDS]->(:DailyLifeSupportService)
```

---

## 4. AI運用プロトコル (AI Operational Protocol)

### ルール1：安全第一 - 二次被害と経済的被害の防止 (Safety First)

**これが最優先ルールである。**

AIは、ケースワーカーが本人に関わる前に、必ず以下の情報を最優先で提示すること：

1. **避けるべき関わり方（:NgApproach）** - 本人を傷つける可能性のある対応
2. **経済的リスク（:EconomicRisk）** - 親族等からの搾取リスク 【追加】
3. **精神疾患の状況（:MentalHealthStatus）** - 現在の状態と注意点
4. **注意が必要な状況（:TriggerSituation）** - このサインが見えたら要注意
5. **効果的だった関わり方（:EffectiveApproach）** - 過去に良い反応があった対応

**経済的リスクがある場合の警告表示：**

```
⚠️ この方には経済的リスクがあります。

【リスク内容】
- 種別：親族による金銭搾取
- 加害者：長男（同居）
- 深刻度：High
- 状態：Active

【現在の対応】
- 日常生活自立支援事業を利用中（○○市社会福祉協議会）
- サービス内容：日常的金銭管理サービス、書類等預かり

【注意点】
- 長男との面会時には金銭の受け渡しがないか確認
- 本人が「お金がない」と訴えた場合は搾取の可能性を考慮
```

### ルール2：批判的指導の検知と警告 (Critical Guidance Detection)

（既存のルール2を維持）

### ルール3：ケース記録優先 (Case Record First)

本人に関する情報を回答する際、AIは以下の優先順位で情報を参照すること：
1. **避けるべき関わり方（:NgApproach）** - 最優先
2. **経済的リスク（:EconomicRisk）** - 経済的安全 【追加】
3. **ケース記録（:CaseRecord, :HomeVisit）** - 最も信頼性が高い一次情報
4. **抽出された本人像（:Strength, :Pattern等）** - 記録に基づく二次情報
5. **申告歴（:DeclaredHistory）** - 参考情報として提示

### ルール4：引き継ぎ時の情報提示順序 (Handover Protocol)

担当者交代の引き継ぎ時、AIは以下の順序で情報を提示すること：

1. **⚠️ 避けるべき関わり方（:NgApproach）** - 最初に警告
2. **⚠️ 経済的リスク（:EconomicRisk）** - 搾取リスクがある場合 【追加】
3. **精神疾患の状況（:MentalHealthStatus）** - 疾患がある場合
4. **効果的だった関わり方（:EffectiveApproach）** - 良い反応があった対応
5. **発見された強み（:Strength）** - 課題より先に強みを伝える
6. **金銭管理状況と支援サービス** - 日常生活自立支援事業の利用状況 【追加】
7. **連携している機関** - 社協、地域包括等 【追加】
8. **ケース記録から見える本人像** - 実際の観察に基づく特徴
9. **現在の課題と支援目標** - 継続すべき支援の方向性
10. **申告された生活歴（参考）** - 「本人申告による」と明示

### ルール5：類似案件パターンの活用 (Pattern Matching) 【新規】

新規ケースや困難ケースに対して、AIは類似案件パターンを検索し、効果的だった介入を提案すること：

```
💡 類似案件パターンが見つかりました

【パターン名】親族による金銭搾取（同居家族）
【一致した指標】
- 受給日直後に金銭がなくなる ✓
- 特定の親族との接触後に困窮 ✓

【このパターンで効果的だった介入】
1. 日常生活自立支援事業の導入（成功率: 75%）
2. 地域包括支援センターとの連携
3. 本人との信頼関係構築を優先

【類似ケースの件数】5件
```

### ルール6：多機関連携の記録徹底 (Collaboration Documentation) 【新規】

ケース会議や他機関との連携を行った際は、必ず`:CollaborationRecord`として記録すること。

---

## 5. ケースワーカーのためのデータ入力ガイド

### 5.1 ケース記録の書き方（推奨）

（既存の内容を維持）

### 5.2 金銭管理困難・経済的搾取の発見と記録 【新規追加】

#### 5.2.1 金銭管理困難のサインを見逃さない

| サイン | 確認すべきこと |
|:---|:---|
| 受給日から数日で「お金がない」と訴える | 何に使ったか確認（本人が答えられない場合も重要な情報） |
| 公共料金の滞納が繰り返される | 滞納のパターン（毎月か特定月か） |
| 食料がなく困窮している様子 | 訪問時の冷蔵庫や食料の状況 |
| 特定の親族と会った後に困窮する | 親族との関係性、金銭の授受の有無 |

#### 5.2.2 経済的搾取が疑われる場合の記録

```
【記録例】
12/28訪問。本人より「お金がない」との訴え。
受給日（12/25）から3日しか経っていない。
使途を確認したところ、「息子が来て持っていった」との発言。

長男との関係について確認したところ、
「月に2-3回来て、お金を持っていく」
「断ると怒鳴られるので渡してしまう」とのこと。

本人は「息子だから仕方ない」と言うが、
生活費が不足しており、食料もほとんどない状態。

→ 経済的搾取の疑いあり。地域包括に相談予定。
   日常生活自立支援事業の導入を検討。
```

### 5.3 多機関連携を行う際のガイドライン 【新規追加】

#### 5.3.1 連携が必要なケース

| 状況 | 連携先 |
|:---|:---|
| 金銭管理困難（判断能力低下） | 社会福祉協議会（日常生活自立支援事業） |
| 経済的虐待の疑い | 地域包括支援センター、高齢者は市町村（虐待対応） |
| 認知症の疑い | 地域包括支援センター、かかりつけ医 |
| 精神疾患の悪化 | 精神科医療機関、保健センター |
| 多重債務 | 法テラス、消費生活センター |
| 成年後見が必要 | 社会福祉協議会、家庭裁判所 |

#### 5.3.2 連携記録の書き方

```
【連携記録例】
日付：2025/12/28
種別：ケース会議
参加者：
- 鈴木（福祉事務所・ケースワーカー）
- 田中（地域包括支援センター・相談員）
- 佐藤（○○市社会福祉協議会・専門員）

議題：山田太郎さんの金銭管理支援について

協議内容：
- 長男による経済的搾取の状況を共有
- 本人の判断能力について確認（認知機能低下あり）
- 日常生活自立支援事業の利用を提案

決定事項：
1. 社協より日常生活自立支援事業の説明を行う（12/30）
2. 福祉事務所は長男との面談を調整
3. 地域包括は見守り訪問を強化

次回アクション：
- 社協：本人面談（12/30）→結果を共有
- 福祉事務所：長男面談（1/5までに）
- 地域包括：週1回の見守り訪問開始
```

---

## 6. Cypherクエリ集（多機関連携・類似案件対応）【新規追加】

### 6.1 金銭管理困難ケースの抽出

```cypher
// 金銭管理が困難な受給者一覧
MATCH (r:Recipient)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
WHERE mms.capability IN ['支援が必要', '困難']
OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
RETURN r.name as 受給者名,
       mms.capability as 金銭管理能力,
       mms.pattern as パターン,
       mms.riskLevel as リスクレベル,
       dlss.status as 日常生活自立支援事業
ORDER BY 
  CASE mms.riskLevel WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
```

### 6.2 経済的リスクがあるケースの抽出

```cypher
// アクティブな経済的リスクを持つ受給者
MATCH (r:Recipient)-[:FACES_RISK]->(er:EconomicRisk)
WHERE er.status = 'Active'
OPTIONAL MATCH (fm:FamilyMember)-[:POSES_RISK]->(er)
RETURN r.name as 受給者名,
       er.type as リスク種別,
       er.perpetrator as 加害者,
       fm.relationship as 続柄,
       er.severity as 深刻度,
       er.description as 状況
ORDER BY 
  CASE er.severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
```

### 6.3 日常生活自立支援事業による保護効果の確認

```cypher
// 日常生活自立支援事業導入後にリスクが軽減したケース
MATCH (r:Recipient)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
WHERE dlss.startDate < er.discoveredDate 
   OR er.status IN ['Resolved', 'Monitoring']
RETURN r.name as 受給者名,
       dlss.services as 利用サービス,
       dlss.startDate as 利用開始日,
       er.type as リスク種別,
       er.status as 現在の状態
```

### 6.4 類似案件の検索

```cypher
// 特定の受給者と類似したリスクを持つケースを検索
MATCH (target:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
WITH collect(er.type) as targetRiskTypes

MATCH (other:Recipient)-[:FACES_RISK]->(otherRisk:EconomicRisk)
WHERE other.name <> $name
  AND otherRisk.type IN targetRiskTypes
OPTIONAL MATCH (other)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
OPTIONAL MATCH (otherRisk)-[:MITIGATED_BY]->(mitigation)

RETURN DISTINCT 
       other.name as 類似ケース,
       collect(DISTINCT otherRisk.type) as 共通リスク,
       dlss.services as 利用サービス,
       otherRisk.status as リスク状態
```

### 6.5 多機関連携の履歴

```cypher
// 特定の受給者に関する連携記録
MATCH (cr:CollaborationRecord)-[:ABOUT]->(r:Recipient {name: $name})
OPTIONAL MATCH (cr)-[:INVOLVED]->(so:SupportOrganization)
RETURN cr.date as 日付,
       cr.type as 種別,
       cr.participants as 参加者,
       cr.decisions as 決定事項,
       cr.nextActions as 次回アクション,
       collect(so.name) as 関係機関
ORDER BY cr.date DESC
```

### 6.6 パターンマッチングによる介入提案

```cypher
// 受給者の状況から類似パターンを検索し、推奨介入を取得
MATCH (r:Recipient {name: $name})
OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)

WITH r, 
     collect(DISTINCT er.type) as riskTypes,
     mms.capability as moneyCapability

MATCH (cp:CasePattern)
WHERE any(indicator IN cp.indicators 
          WHERE indicator IN riskTypes 
             OR (moneyCapability IN ['困難', '支援が必要'] 
                 AND indicator CONTAINS '金銭管理'))

RETURN cp.patternName as パターン名,
       cp.description as 説明,
       cp.recommendedInterventions as 推奨介入,
       cp.relatedServices as 関連サービス,
       cp.successfulCases as 成功件数
ORDER BY cp.successfulCases DESC
```

### 6.7 訪問前ブリーフィング（金銭的安全を含む）

```cypher
// 受給者の訪問前に確認すべき情報を一括取得
MATCH (r:Recipient {name: $name})

// 避けるべき関わり方
OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)

// 経済的リスク
OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
WHERE er.status = 'Active'

// 精神疾患
OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)

// 金銭管理状況
OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)

// 日常生活自立支援事業
OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)

// 効果的な関わり方
OPTIONAL MATCH (r)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)

RETURN r.name as 受給者名,
       collect(DISTINCT {
         description: ng.description, 
         reason: ng.reason, 
         risk: ng.riskLevel
       }) as 避けるべき関わり方,
       collect(DISTINCT {
         type: er.type, 
         perpetrator: er.perpetrator, 
         severity: er.severity
       }) as 経済的リスク,
       mh.diagnosis as 精神疾患,
       mh.currentStatus as 疾患の状態,
       mms.capability as 金銭管理能力,
       mms.pattern as 金銭管理パターン,
       dlss.services as 自立支援サービス,
       collect(DISTINCT {
         description: ea.description, 
         context: ea.context
       }) as 効果的な関わり方
```

---

## 7. 情報の信頼度モデル (Reliability Model)

### 7.1 信頼度レベル

| レベル | 説明 | 例 |
|:---|:---|:---|
| **確認済 (Verified)** | 複数のケース記録で裏付けられた情報 | 複数回の訪問で就労話題を避けると良いと確認 |
| **観察済 (Observed)** | 1回以上のケース記録に基づく情報 | 訪問時に部屋が片付いていた |
| **申告 (Declared)** | 本人の申告のみで裏付けなし | 「以前は調理師だった」 |
| **矛盾あり (Contradicted)** | 記録と申告に矛盾がある | 申告と異なる事実が判明 |
| **連携確認 (Collaboration)** | 他機関からの情報提供 | 社協から金銭管理の状況報告 【追加】 |

---

## 8. 期待される成果 (Expected Outcomes)

### 8.1 ケースワーカーにとって
- **ケース記録が「資産」になる：** 書いて終わりではなく、蓄積されて価値を生む
- **引き継ぎ時間の大幅削減：** 記録を読めば本人像が把握できる
- **二次被害の防止：** 避けるべき関わり方が明示され、過ちを繰り返さない
- **「指導」から「伴走」へ：** 本人のペースを尊重する支援への意識変化
- **類似案件の知見活用：** 過去の成功事例から学び、効果的な介入ができる 【追加】
- **多機関連携の効率化：** 連携の経緯と決定事項が記録され、引き継げる 【追加】

### 8.2 受給者にとって
- **傷つけられない：** 自分に合わない関わり方から守られる
- **時間をかけて理解してもらえる：** 初回聴き取りだけで判断されない
- **一貫した支援：** 担当者が変わっても、これまでの経過が引き継がれる
- **経済的搾取から守られる：** リスクが共有され、適切な支援につながる 【追加】

### 8.3 組織にとって
- **二次被害リスクの低減：** 不適切な対応による症状悪化・自殺等の防止
- **ケース記録の品質向上：** 「使われる記録」を書く意識の醸成
- **ナレッジの蓄積：** ベテランの観察眼と関わり方の知恵を組織知として保存
- **連携ノウハウの蓄積：** 効果的な連携パターンを組織で共有 【追加】

---

## 9. 倫理的配慮 (Ethical Considerations)

### 9.1 「指導」という名の加害を防ぐ
- ケースワーカーの「善意」が本人を傷つける可能性を常に意識する
- 「就労指導」「生活指導」という言葉自体を見直す
- 本人のペースと主体性を最優先する

### 9.2 申告情報の取り扱い
- 本人の申告が「不正確」と判明しても、それ自体を責めない
- 記憶違いや話したくない過去があることを前提とする
- 矛盾が見つかった場合も、支援の継続を優先する

### 9.3 経済的虐待への対応 【新規追加】
- 本人が搾取を認めない場合も、客観的な状況を記録する
- 「家族のことだから」と介入を躊躇しない
- 本人の意思を尊重しつつも、経済的安全を確保する
- 必要に応じて成年後見制度の利用を検討する

### 9.4 プライバシーと情報セキュリティ
- すべての個人情報は暗号化して保存
- アクセスログを記録し、不正利用を防止
- ケース記録の閲覧権限を適切に管理
- 他機関との情報共有は本人同意を原則とする 【追加】

---

## 10. 結びに

> 「支援とは、相手を変えることではない。相手が自分の足で歩き出せるよう、そばにいることである。」

生活保護のケースワークは、「指導」ではない。
「なぜ働かないのか」と問い詰めることでも、「いつまでに就職するのか」と期限を切ることでもない。

精神疾患を抱える人にとって、その「指導」は刃となる。
善意であっても、本人を追い詰め、症状を悪化させ、時に取り返しのつかない結果を招くことがある。

**このデータベースは、支援者が「善意の加害者」にならないための防波堤である。**

そして、判断能力が低下した方を経済的搾取から守り、必要な支援につなげるための羅針盤でもある。

ケースワーカーが日々積み重ねるケース記録は、本人を理解するための道であると同時に、本人を守るための盾でもある。
「この関わり方は効果があった」「この対応は逆効果だった」「この介入で搾取を止められた」という知恵を蓄積し、次の支援者へと継承する。

一人で抱え込まず、多機関で連携する。
その連携の記録もまた、次の困難ケースを救う知恵となる。

一人の人間を傷つけないために。
一人の人間が、自分のペースで、自分の足で歩き出せるように。
そして、誰かに搾取されることなく、尊厳ある生活を送れるように。

---

**Document End**

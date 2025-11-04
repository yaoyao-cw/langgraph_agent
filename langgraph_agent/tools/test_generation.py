"""Tools dedicated to the test generation workflow."""
from __future__ import annotations

import json
import re
import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from ..config import settings
from ..utils.console import ACCENT_COLOR, INFO_COLOR, RESET, pretty_sub_line, pretty_tool_line

try:  # pragma: no cover - optional dependency resolution
    from test_case_generator.src.models.function_schema import FunctionDefinitionInput
    from test_case_generator.src.tools.signal_traversal_tool import LogicCompletenessGenerator
except Exception as exc:  # pragma: no cover - import guard
    raise RuntimeError(
        "Install with: pip install langchain-anthropic langgraph langchain-core"
    ) from exc


TEST_GENERATOR: Optional[LogicCompletenessGenerator] = None
llm = None


def bind_language_model(model: Any) -> None:
    """Bind the language model instance used for inference tools."""
    global llm
    llm = model


@tool
def initialize_test_gen(json_data: str) -> str:
    """Initialize the test case generator with function definition from JSON."""
    pretty_tool_line("InitTestGen", "Parsing JSON data")

    global TEST_GENERATOR

    try:
        data = json.loads(json_data) if isinstance(json_data, str) else json_data
        function_def = FunctionDefinitionInput.model_validate(data)
        TEST_GENERATOR = LogicCompletenessGenerator(function_def)

        result = (
            f"✓ Initialized test generator for function: {function_def.functionName}\n"
            f"  - Power modes: {len(function_def.powerModes or [])}\n"
            f"  - CAN signals: {len(function_def.signalInterface.CAN)}\n"
            f"  - Logic paths: {len(function_def.logicFlow.paths)}"
        )

        pretty_sub_line(result)
        return result

    except Exception as err:  # pragma: no cover - defensive branch
        error_msg = f"Failed to initialize: {err}"
        pretty_sub_line(error_msg)
        traceback.print_exc()
        return error_msg


@tool
def extract_covered_combinations() -> str:
    """Extract already covered test combinations from existing test cases."""
    pretty_tool_line("ExtractCovered", "Analyzing existing test coverage")

    if TEST_GENERATOR is None:
        error = "⚠️ Test generator not initialized. Call initialize_test_gen first."
        pretty_sub_line(error)
        return error

    try:
        TEST_GENERATOR._extract_covered_combinations()

        covered_count = len(TEST_GENERATOR.covered_combinations)
        result: Dict[str, Any] = {
            "status": "success",
            "covered_count": covered_count,
            "sample_combinations": [],
        }

        for i, combo in enumerate(TEST_GENERATOR.covered_combinations[:3]):
            try:
                result["sample_combinations"].append(
                    {
                        "index": i + 1,
                        "source": combo.source.pathId,
                        "display": combo.format_display(),
                    }
                )
            except Exception as err:  # pragma: no cover - formatting fallback
                result["sample_combinations"].append(
                    {"index": i + 1, "error": str(err)}
                )

        result_str = json.dumps(result, indent=2, ensure_ascii=False)

        summary = f"✓ Extracted {covered_count} covered combinations"
        if covered_count > 0:
            summary += "\n  First few examples:\n"
            for sample in result["sample_combinations"]:
                if "display" in sample:
                    summary += (
                        f"  {sample['index']}. {sample['source']}: {sample['display']}\n"
                    )

        pretty_sub_line(summary)
        return result_str

    except Exception as err:  # pragma: no cover - defensive branch
        error_msg = f"❌ Error extracting combinations: {err}"
        pretty_sub_line(error_msg)
        traceback.print_exc()
        return json.dumps({"status": "error", "message": error_msg})


@tool
def execute_strategies() -> str:
    """Generate test combinations using strategies (without inferring outputs)."""
    pretty_tool_line("ExecuteStrategies", "Generating test combinations")

    if TEST_GENERATOR is None:
        return json.dumps({"error": "Test generator not initialized"})

    if not TEST_GENERATOR.covered_combinations:
        return json.dumps({"error": "No covered combinations. Call extract_covered_combinations first"})

    try:
        TEST_GENERATOR._execute_strategies()
        total = sum(
            len(combos) for combos in TEST_GENERATOR.generated_combinations.values()
        )

        result = {
            "status": "success",
            "total_generated": total,
            "by_strategy": {
                name: len(combos)
                for name, combos in TEST_GENERATOR.generated_combinations.items()
            },
            "note": "Outputs are empty. Call infer_outputs_with_ai to infer expected results.",
        }

        summary = f"✓ Generated {total} combinations (outputs empty)\n"
        for name, count in result["by_strategy"].items():
            summary += f"  - {name}: {count}\n"

        pretty_sub_line(summary)
        return json.dumps(result, ensure_ascii=False)

    except Exception as err:  # pragma: no cover - defensive branch
        pretty_sub_line(f"Error: {err}")
        traceback.print_exc()
        return json.dumps({"error": str(err)})


@tool
def infer_outputs_with_ai() -> str:
    """Infer expected outputs for generated combinations using the bound language model."""
    pretty_tool_line("InferOutputs", "AI语义推理中")

    if not TEST_GENERATOR or not TEST_GENERATOR.generated_combinations:
        return json.dumps([])

    if llm is None:  # pragma: no cover - configuration guard
        raise RuntimeError("Language model has not been bound. Call bind_language_model first.")

    func = TEST_GENERATOR.function_def

    signals_def: Dict[str, Dict[str, str]] = {}
    if func.powerModes:
        signals_def["powerMode"] = {pm: f"电源{pm}状态" for pm in func.powerModes}

    for sig in func.signalInterface.CAN:
        signals_def[sig.signalName] = {v.value: v.description for v in sig.definedValues}

    for sig in func.signalInterface.HARDWIRE:
        signals_def[sig.signalName] = {v.value: v.description for v in sig.definedValues}

    paths_info: List[Dict[str, Any]] = []
    for path in func.logicFlow.paths:
        path_data = {
            "pathId": path.pathId,
            "description": path.pathDescription,
            "conditions": {
                "preconditions": [],
                "trigger": {"logic": path.conditions.trigger.logic, "signals": []},
            },
            "outputs_template": path.outputs.model_dump(),
        }

        for pc in path.conditions.preconditions:
            if pc.type == "powerMode":
                values = pc.value if isinstance(pc.value, list) else [pc.value]
                path_data["conditions"]["preconditions"].append(
                    {
                        "signal": "powerMode",
                        "required_values": [
                            f"{v}({signals_def['powerMode'].get(v, v)})" for v in values
                        ],
                    }
                )
            else:
                values = pc.value if isinstance(pc.value, list) else [pc.value]
                sig_defs = signals_def.get(pc.signalName, {})
                path_data["conditions"]["preconditions"].append(
                    {
                        "signal": pc.signalName,
                        "required_values": [
                            f"{v}({sig_defs.get(v, '未知')})" for v in values
                        ],
                    }
                )

        for sig in path.conditions.trigger.signals:
            values = sig.value if isinstance(sig.value, list) else [sig.value]
            sig_defs = signals_def.get(sig.signalName, {})
            path_data["conditions"]["trigger"]["signals"].append(
                {
                    "signal": sig.signalName,
                    "required_values": [
                        f"{v}({sig_defs.get(v, '未知')})" for v in values
                    ],
                }
            )

        paths_info.append(path_data)

    if not paths_info:
        return json.dumps([])

    combos_list: List[Dict[str, Any]] = []
    for strategy, combos in TEST_GENERATOR.generated_combinations.items():
        for idx, combo in enumerate(combos):
            cid = f"{strategy}_{idx + 1}"

            pre: Dict[str, str] = {}
            if combo.preconditions.power_mode:
                pm = combo.preconditions.power_mode
                pre["powerMode"] = f"{pm}({signals_def.get('powerMode', {}).get(pm, '未知')})"
            if combo.preconditions.can_signal:
                sig_name = combo.preconditions.can_signal.signalName
                sig_val = combo.preconditions.can_signal.value
                desc = signals_def.get(sig_name, {}).get(sig_val, "未知")
                pre[sig_name] = f"{sig_val}({desc})"

            trg: Dict[str, str] = {}
            for sig in combo.trigger.can_signals:
                desc = signals_def.get(sig.signalName, {}).get(sig.value, "未知")
                trg[sig.signalName] = f"{sig.value}({desc})"

            combos_list.append({"id": cid, "preconditions": pre, "trigger": trg})

    prompt = f"""# 任务：基于语义推理测试组合的预期输出

## 完整信号定义
{json.dumps(signals_def, indent=2, ensure_ascii=False)}

## 已知逻辑路径（共{len(paths_info)}个）

"""

    for path in paths_info:
        prompt += f"""
### 路径: {path['pathId']}
**功能描述**: {path['description']}

**前置条件要求**:
"""
        for cond in path["conditions"]["preconditions"]:
            prompt += f"- {cond['signal']} 必须是: {', '.join(cond['required_values'])}\n"

        prompt += f"\n**触发条件要求 ({path['conditions']['trigger']['logic']})**:\n"
        for sig in path["conditions"]["trigger"]["signals"]:
            prompt += f"- {sig['signal']} 必须是: {', '.join(sig['required_values'])}\n"

        prompt += (
            "\n**路径输出模板**（⭐这是推理的唯一模板⭐）:\n"
            f"```json\n{json.dumps(path['outputs_template'], indent=2, ensure_ascii=False)}\n```\n"
            "---\n"
        )

    prompt += f"""
    ## 推理规则（⭐核心逻辑⭐）

    ### 第一步：语义匹配判断

    对于每个组合，检查其信号值的**描述**是否与路径要求的**描述语义相同或相近**：

    **示例1：语义同类**
    - 路径要求: EspAbsFailr必须是 "0x1(故障)" 或 "0x2(严重故障)"
    - 组合值: EspAbsFailr = "0x3(超级故障)"
    - 分析: "超级故障"和"故障"、"严重故障"都含"故障"关键词，属于同一类
    - 结论: ✅ 语义匹配

    **示例2：语义不同类**
    - 路径要求: EspAbsFailr必须是 "0x1(故障)" 或 "0x2(严重故障)"
    - 组合值: EspAbsFailr = "0x0(无故障)"
    - 分析: "无故障"表示正常，和"故障类"相反
    - 结论: ❌ 语义不匹配

    **示例3：语义不同类**
    - 路径要求: EspAbsFailr必须是 "0x1(故障)" 或 "0x2(严重故障)"
    - 组合值: EspAbsFailr = "0x4(无)"
    - 分析: "无"表示没有故障，和"故障类"不同
    - 结论: ❌ 语义不匹配

    **示例4：电源状态**
    - 路径要求: powerMode必须是 "ON" 或 "ACC"
    - 组合值: powerMode = "OFF"
    - 分析: "OFF"不在要求列表中，语义不匹配
    - 结论: ❌ 语义不匹配

    ### 第二步：推断输出

    #### 情况A：所有条件都语义匹配
    → **原样使用路径的outputs模板**

    #### 情况B：任一条件语义不匹配
    → **基于路径outputs模板推断相反状态**：

       **indicators** - 修改action字段：
       - "点亮" → "熄灭"
       - "闪烁" → "熄灭"
       - "常亮" → "熄灭"

       **texts** - 展示/不展示（⭐内容不变⭐）：
       - 匹配时：保留数组内容（展示文本）
       - 不匹配时：清空数组 [] （不展示文本）

       **sounds** - 播放/不播放：
       - 匹配时：保留数组内容（播放声音）
       - 不匹配时：清空数组 [] （不播放声音）

       **images** - 显示/不显示：
       - 匹配时：保留数组内容（显示图片）
       - 不匹配时：清空数组 [] （不显示图片）

    **推断示例1**：

    路径outputs模板:
    ```json
    {{
      "indicators": [{{"name": "ABS故障指示灯", "action": "点亮"}}],
      "texts": [],
      "sounds": [],
      "images": []
    }}
    ```

    ✅ 匹配时 → 原样:
    ```json
    {{
      "indicators": [{{"name": "ABS故障指示灯", "action": "点亮"}}],
      "texts": [],
      "sounds": [],
      "images": []
    }}
    ```

    ❌ 不匹配时 → 推断相反:
    ```json
    {{
      "indicators": [{{"name": "ABS故障指示灯", "action": "熄灭"}}],
      "texts": [],
      "sounds": [],
      "images": []
    }}
    ```

## 待推理组合（共{len(combos_list)}个）

"""

    for combo in combos_list[:40]:
        prompt += (
            f"{combo['id']}: 前置{combo['preconditions']}, 触发{combo['trigger']}\n"
        )

    prompt += """
## 输出格式

返回JSON数组，格式：
```json
[
  {
    "combination_id": "组合ID",
    "matched": true/false,
    "reasoning": "简短说明：哪些条件匹配/不匹配，为什么",
    "outputs": {严格按照路径模板的结构}
  }
]
```

**重要提醒**：
1. outputs必须严格遵循路径outputs模板的结构
2. 不能添加路径模板中没有的字段
3. 路径模板中为空的字段必须保持空
4. 只在路径模板有内容的字段中推断相反状态

请开始推理所有{len(combos_list)}个组合。
"""

    print(f"{INFO_COLOR}  🤖 LLM语义推理{len(combos_list)}个组合...{RESET}")
    response = llm.invoke(
        [
            SystemMessage(
                content="你是测试推理专家。基于信号描述的语义进行推理，严格遵循输出模板。"
            ),
            HumanMessage(content=prompt),
        ]
    )

    content = response.content if isinstance(response.content, str) else str(response.content)

    results: List[Dict[str, Any]] = []
    try:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            parsed = json.loads(match.group(1))
        else:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                parsed = json.loads(content)

        if isinstance(parsed, list):
            results = parsed
            print(f"{INFO_COLOR}  ✓ 成功解析{len(results)}个推理结果{RESET}")
    except Exception as err:
        print(f"{ACCENT_COLOR}  ⚠️ JSON解析失败: {err}{RESET}")

    existing_ids = {r.get("combination_id") for r in results}
    default_outputs = {"indicators": [], "texts": [], "sounds": [], "images": []}

    for combo in combos_list:
        if combo["id"] not in existing_ids:
            template = paths_info[0]["outputs_template"] if paths_info else default_outputs
            results.append(
                {
                    "combination_id": combo["id"],
                    "matched": False,
                    "reasoning": "LLM未推理，使用默认",
                    "outputs": template,
                }
            )

    final_results: List[Dict[str, Any]] = []
    for r in results:
        final_results.append(
            {
                "combination_id": r["combination_id"],
                "reasoning": r.get("reasoning", "无推理说明"),
                "outputs": r.get("outputs", default_outputs),
            }
        )

    pretty_sub_line(f"✓ 推理完成: {len(final_results)}个")

    print(f"\n{INFO_COLOR}推理示例:{RESET}")
    for r in final_results[:3]:
        summary_parts = []
        for key, val in r["outputs"].items():
            if val and len(val) > 0:
                summary_parts.append(f"{key}×{len(val)}")
        summary = ", ".join(summary_parts) if summary_parts else "空"
        print(f"  {r['combination_id']}: {summary}")
        print(f"    推理: {r['reasoning'][:200]}...")

    return json.dumps(final_results, ensure_ascii=False)


@tool
def apply_inferred_outputs(inferred_results: str) -> str:
    """Apply AI inferred outputs back onto generated combinations."""
    pretty_tool_line("ApplyOutputs", "应用推理结果")

    if not TEST_GENERATOR:
        return json.dumps({"error": "未初始化"})

    try:
        results = json.loads(inferred_results) if isinstance(inferred_results, str) else inferred_results
        applied = 0

        for item in results:
            cid = item.get("combination_id", "")
            outputs = item.get("outputs", {})

            if not cid:
                continue

            parts = cid.rsplit("_", 1)
            if len(parts) != 2:
                continue

            strategy_name, idx_str = parts

            if strategy_name not in TEST_GENERATOR.generated_combinations:
                continue

            try:
                idx = int(idx_str) - 1
                combos = TEST_GENERATOR.generated_combinations[strategy_name]

                if 0 <= idx < len(combos):
                    combos[idx].outputs = {
                        "indicators": outputs.get("indicators", []),
                        "texts": outputs.get("texts", []),
                        "sounds": outputs.get("sounds", []),
                        "images": outputs.get("images", []),
                    }
                    applied += 1

                    if applied <= 3:
                        action = (
                            combos[idx].outputs["indicators"][0]["action"]
                            if combos[idx].outputs["indicators"]
                            else "无"
                        )
                        print(f"{INFO_COLOR}  [Debug] {cid} -> {action}{RESET}")

            except Exception as err:  # pragma: no cover - defensive branch
                print(f"{ACCENT_COLOR}  [Error] {cid}: {err}{RESET}")
                continue

        pretty_sub_line(f"✅ 应用: {applied}/{len(results)}")

        sample_combo = None
        for strategy_name, combos in TEST_GENERATOR.generated_combinations.items():
            if combos:
                sample_combo = combos[0]
                break

        if sample_combo and sample_combo.outputs:
            print(f"{INFO_COLOR}  [验证] 示例outputs: {sample_combo.outputs}{RESET}")
        else:
            print(f"{ACCENT_COLOR}  [警告] 示例组合的outputs仍为空！{RESET}")

        return json.dumps({"status": "success", "applied": applied, "total": len(results)})

    except Exception as err:  # pragma: no cover - defensive branch
        error_msg = f"Error: {err}"
        pretty_sub_line(error_msg)
        traceback.print_exc()
        return json.dumps({"error": error_msg})


@tool
def get_test_results() -> str:
    """Collect generation statistics and persist them to disk."""
    pretty_tool_line("GetResults", "Collecting test results")

    if TEST_GENERATOR is None:
        error = "⚠️ Test generator not initialized."
        pretty_sub_line(error)
        return error

    try:
        result = {
            "function_name": TEST_GENERATOR.function_def.functionName,
            "covered_combinations": len(TEST_GENERATOR.covered_combinations),
            "generated_combinations": {},
            "total_generated": 0,
        }

        total = 0
        for strategy_name, combos in TEST_GENERATOR.generated_combinations.items():
            count = len(combos)
            total += count
            result["generated_combinations"][strategy_name] = count

        result["total_generated"] = total

        output_file = settings.workspace / "test_generation_results.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        summary = (
            "✓ Test generation completed!\n"
            f"  Function: {result['function_name']}\n"
            f"  Covered: {result['covered_combinations']} combinations\n"
            f"  Generated: {result['total_generated']} new combinations\n"
            f"  Results saved to: {output_file.relative_to(settings.workspace)}"
        )

        pretty_sub_line(summary)
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as err:  # pragma: no cover - defensive branch
        error_msg = f"❌ Error getting results: {err}"
        pretty_sub_line(error_msg)
        traceback.print_exc()
        return json.dumps({"status": "error", "message": error_msg})


@tool
def export_test_cases(output_format: str = "json") -> str:
    """Export generated test cases in the requested format."""
    pretty_tool_line("ExportCases", f"导出{output_format}格式")

    if not TEST_GENERATOR:
        return json.dumps({"error": "未初始化"})

    try:
        all_cases = []
        case_id = 1

        for strategy_name, combos in TEST_GENERATOR.generated_combinations.items():
            for combo in combos:
                preconditions: Dict[str, Any] = {}
                if combo.preconditions.power_mode:
                    preconditions["powerMode"] = combo.preconditions.power_mode
                if combo.preconditions.can_signal:
                    preconditions[
                        combo.preconditions.can_signal.signalName
                    ] = combo.preconditions.can_signal.value

                trigger_signals: Dict[str, Any] = {}
                for sig in combo.trigger.can_signals:
                    trigger_signals[sig.signalName] = sig.value

                outputs = (
                    combo.outputs
                    if combo.outputs
                    else {"indicators": [], "texts": [], "sounds": [], "images": []}
                )

                test_case = {
                    "id": f"TC_{case_id:03d}",
                    "strategy": strategy_name,
                    "preconditions": preconditions,
                    "trigger": {
                        "logic": combo.trigger.logic,
                        "signals": trigger_signals,
                    },
                    "expected_outputs": outputs,
                    "source": combo.source.pathId,
                }

                all_cases.append(test_case)
                case_id += 1

        with_outputs = sum(
            1 for c in all_cases if any(c["expected_outputs"].values())
        )

        if output_format == "json":
            output_file = settings.workspace / "generated_test_cases.json"
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "function": TEST_GENERATOR.function_def.functionName,
                        "total_cases": len(all_cases),
                        "with_outputs": with_outputs,
                        "without_outputs": len(all_cases) - with_outputs,
                        "test_cases": all_cases,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        else:
            output_file = settings.workspace / "generated_test_cases.md"
            lines = [
                f"# {TEST_GENERATOR.function_def.functionName} 测试用例\n",
                f"**总计**: {len(all_cases)} 个用例\n",
                f"**有预期**: {with_outputs} 个\n",
            ]

            for case in all_cases:
                lines.append(f"\n## {case['id']} - {case['strategy']}\n")
                lines.append(f"**前置**: {case['preconditions']}\n")
                lines.append(
                    f"**触发**: {case['trigger']['signals']}\n"
                )
                lines.append("**预期**:")
                if case["expected_outputs"]["indicators"]:
                    for ind in case["expected_outputs"]["indicators"]:
                        lines.append(
                            f"  - {ind['name']}: {ind['action']}"
                        )
                else:
                    lines.append("  - 无")
                lines.append("")

            output_file.write_text("\n".join(lines), encoding="utf-8")

        summary = (
            f"✓ 导出 {len(all_cases)} 个用例\n"
            f"  - 有预期: {with_outputs}\n"
            f"  - 无预期: {len(all_cases) - with_outputs}"
        )

        if len(all_cases) - with_outputs > 0:
            summary += (
                f"\n  ⚠️ 警告: {len(all_cases) - with_outputs} 个用例没有预期！"
            )

        pretty_sub_line(summary)
        return str(output_file)

    except Exception as err:  # pragma: no cover - defensive branch
        error_msg = f"Error: {err}"
        pretty_sub_line(error_msg)
        traceback.print_exc()
        return error_msg


__all__ = [
    "apply_inferred_outputs",
    "bind_language_model",
    "execute_strategies",
    "export_test_cases",
    "extract_covered_combinations",
    "get_test_results",
    "infer_outputs_with_ai",
    "initialize_test_gen",
]

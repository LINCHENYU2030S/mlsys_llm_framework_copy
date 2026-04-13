from functools import lru_cache
import re


PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
HORIZONTAL_WHITESPACE = " \t\r"
SENTENCE_TERMINATORS = ".?!"
CLOSING_PUNCTUATION = "\"')}]"


def _contains_placeholder(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def _join_segments(
    segments: list[str],
    separators: list[str],
    trailing_separator: str = "",
) -> str:
    if not segments:
        return trailing_separator

    parts = [segments[0]]
    for separator, segment in zip(separators, segments[1:]):
        parts.append(separator)
        parts.append(segment)
    parts.append(trailing_separator)
    return "".join(parts)


def _split_template(
    prompt_template: str,
) -> tuple[list[str], list[str], str]:
    segments: list[str] = []
    separators: list[str] = []
    current: list[str] = []
    pending_separator = ""

    i = 0
    while i < len(prompt_template):
        ch = prompt_template[i]

        if pending_separator and not current:
            if segments:
                separators.append(pending_separator)
            else:
                current.append(pending_separator)
            pending_separator = ""

        if ch == "\n":
            segment_text = "".join(current)
            stripped_segment = segment_text.rstrip(HORIZONTAL_WHITESPACE)
            trailing_hspace = segment_text[len(stripped_segment):]

            if stripped_segment:
                segments.append(stripped_segment)
            else:
                trailing_hspace = segment_text

            current.clear()

            j = i
            while j < len(prompt_template) and prompt_template[j] in HORIZONTAL_WHITESPACE + "\n":
                j += 1

            pending_separator += trailing_hspace + prompt_template[i:j]
            i = j
            continue

        if ch in SENTENCE_TERMINATORS:
            j = i
            while j < len(prompt_template) and prompt_template[j] in SENTENCE_TERMINATORS:
                current.append(prompt_template[j])
                j += 1
            while j < len(prompt_template) and prompt_template[j] in CLOSING_PUNCTUATION:
                current.append(prompt_template[j])
                j += 1

            if j == len(prompt_template) or prompt_template[j].isspace():
                segments.append("".join(current))
                current.clear()

                k = j
                while k < len(prompt_template) and prompt_template[k] in HORIZONTAL_WHITESPACE:
                    k += 1

                pending_separator += prompt_template[j:k]
                i = k
                continue

            i = j
            continue

        current.append(ch)
        i += 1

    if current:
        if pending_separator:
            if segments:
                separators.append(pending_separator)
            else:
                current.insert(0, pending_separator)
            pending_separator = ""
        segments.append("".join(current))

    return segments, separators, pending_separator


@lru_cache(maxsize=4096)
def rewrite_prompt_template_for_prefix_caching(prompt_template: str) -> str:
    segments, separators, trailing_separator = _split_template(prompt_template)
    if len(segments) < 2:
        return prompt_template

    suffix_start = len(segments)
    while suffix_start > 0 and not _contains_placeholder(segments[suffix_start - 1]):
        suffix_start -= 1

    if suffix_start == len(segments) or suffix_start == 0:
        return prompt_template

    bridge_separator = separators[suffix_start - 1]
    moved_segments = segments[suffix_start:]
    moved_separators = separators[suffix_start:]
    prefix_segments = segments[:suffix_start]
    prefix_separators = separators[: suffix_start - 1]

    rewritten_prompt_template = (
        _join_segments(moved_segments, moved_separators)
        + bridge_separator
        + _join_segments(prefix_segments, prefix_separators)
        + trailing_separator
    )

    # print("[prompt-rewrite] before:")
    # print(prompt_template)
    # print("[prompt-rewrite] after:")
    # print(rewritten_prompt_template)

    return rewritten_prompt_template

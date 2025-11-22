#!/usr/bin/env python3
"""
LiveKit Voice Agent Prompt Validator

This script validates voice agent prompts against best practices
and identifies common issues that affect voice/TTS output quality.

Usage:
    python validate_prompt.py <prompt_file>
    python validate_prompt.py -          # Read from stdin
    echo "prompt text" | python validate_prompt.py -

Examples:
    python validate_prompt.py my_prompt.txt
    python validate_prompt.py agent_instructions.md
    cat prompt.txt | python validate_prompt.py -
"""

import sys
import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the prompt."""
    severity: str  # 'error', 'warning', 'info'
    category: str
    message: str
    line_number: int = None
    suggestion: str = None


class PromptValidator:
    """Validates LiveKit voice agent prompts."""

    def __init__(self, prompt: str):
        self.prompt = prompt
        self.lines = prompt.split('\n')
        self.issues: List[ValidationIssue] = []

    def validate(self) -> List[ValidationIssue]:
        """Run all validation checks."""
        self.check_identity()
        self.check_voice_optimization()
        self.check_special_characters()
        self.check_length()
        self.check_formatting_mentions()
        self.check_response_length_guidance()
        self.check_number_formatting()
        self.check_tool_usage()
        return self.issues

    def check_identity(self):
        """Check for identity section (You are...)."""
        has_identity = any(
            line.strip().lower().startswith('you are')
            for line in self.lines
        )

        if not has_identity:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='Identity',
                message='Prompt should start with clear identity statement ("You are...")',
                suggestion='Add an identity section like: "You are [name], a [role]. You are [traits]."'
            ))

    def check_voice_optimization(self):
        """Check for voice optimization instructions."""
        prompt_lower = self.prompt.lower()

        # Check for plain text instruction
        has_plain_text = any(keyword in prompt_lower for keyword in [
            'plain text',
            'no formatting',
            'no special formatting',
            'no markdown'
        ])

        if not has_plain_text:
            self.issues.append(ValidationIssue(
                severity='error',
                category='Voice Optimization',
                message='Missing plain text formatting instruction (critical for TTS)',
                suggestion='Add: "Respond in plain text only - no emojis, markdown, or special formatting."'
            ))

        # Check for brevity instruction
        has_brevity = any(keyword in prompt_lower for keyword in [
            'brief',
            'concise',
            'short',
            '1-3 sentences',
            '1-2 sentences'
        ])

        if not has_brevity:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='Voice Optimization',
                message='Missing response length guidance',
                suggestion='Add: "Keep your responses brief - typically 1-3 sentences."'
            ))

    def check_special_characters(self):
        """Check for problematic characters in the prompt itself."""
        problematic_chars = {
            '😊': 'emojis',
            '👍': 'emojis',
            '✨': 'emojis',
            '❌': 'emojis',
            '✓': 'special symbols',
            '•': 'bullet points',
            '→': 'arrows',
        }

        for char, char_type in problematic_chars.items():
            if char in self.prompt:
                for i, line in enumerate(self.lines, 1):
                    if char in line:
                        self.issues.append(ValidationIssue(
                            severity='warning',
                            category='Special Characters',
                            message=f'Prompt contains {char_type} ({char}) which may confuse TTS',
                            line_number=i,
                            suggestion=f'Remove {char_type} from prompt instructions'
                        ))

        # Check for dollar signs (should spell out prices for voice)
        if '$' in self.prompt:
            for i, line in enumerate(self.lines, 1):
                if '$' in line and not any(skip in line.lower() for skip in ['omit', 'not "$', 'say "', 'don\'t']):
                    self.issues.append(ValidationIssue(
                        severity='info',
                        category='Number Formatting',
                        message='Prompt contains $ symbol which is not voice-friendly',
                        line_number=i,
                        suggestion='Spell out prices in prompts (e.g., "twelve dollars" not "$12")'
                    ))

    def check_length(self):
        """Check prompt length."""
        word_count = len(self.prompt.split())

        if word_count > 500:
            self.issues.append(ValidationIssue(
                severity='warning',
                category='Length',
                message=f'Prompt is quite long ({word_count} words). Long prompts may cause inconsistent behavior.',
                suggestion='Consider simplifying or splitting into multiple agents (for multi-agent systems).'
            ))
        elif word_count < 20:
            self.issues.append(ValidationIssue(
                severity='info',
                category='Length',
                message=f'Prompt is very short ({word_count} words).',
                suggestion='Ensure all necessary voice optimization rules are included.'
            ))

    def check_formatting_mentions(self):
        """Check if prompt asks for formatting that TTS can't handle."""
        problematic_patterns = [
            (r'\*\*bold\*\*', 'markdown bold formatting'),
            (r'__bold__', 'markdown bold formatting'),
            (r'_italic_', 'markdown italic formatting'),
            (r'\*italic\*', 'markdown italic formatting'),
            (r'```', 'code blocks'),
            (r'`code`', 'inline code formatting'),
            (r'emoji', 'emojis'),
            (r'bullet.*list', 'bullet lists'),
            (r'numbered.*list', 'numbered lists'),
            (r'table', 'tables'),
        ]

        prompt_lower = self.prompt.lower()

        for pattern, description in problematic_patterns:
            if re.search(pattern, prompt_lower):
                # Check if it's in a "don't use" context
                context_lines = []
                for i, line in enumerate(self.lines):
                    if re.search(pattern, line.lower()):
                        # Check surrounding context
                        context = ' '.join(self.lines[max(0, i-1):min(len(self.lines), i+2)]).lower()
                        if not any(neg in context for neg in ['no ', 'never ', 'don\'t ', 'avoid ', 'without ']):
                            self.issues.append(ValidationIssue(
                                severity='warning',
                                category='Formatting',
                                message=f'Prompt mentions {description} without clearly forbidding it',
                                line_number=i+1,
                                suggestion=f'Ensure instructions clearly state NOT to use {description}'
                            ))

    def check_response_length_guidance(self):
        """Check for one-question-at-a-time guidance."""
        prompt_lower = self.prompt.lower()

        has_one_question = any(phrase in prompt_lower for phrase in [
            'one question at a time',
            'ask one question',
            'single question'
        ])

        # Only warn if prompt seems to involve collecting information
        collects_info = any(keyword in prompt_lower for keyword in [
            'collect',
            'ask for',
            'gather',
            'information',
            'details'
        ])

        if collects_info and not has_one_question:
            self.issues.append(ValidationIssue(
                severity='info',
                category='Conversation Flow',
                message='Prompt involves collecting information but doesn\'t specify asking one question at a time',
                suggestion='Add: "Ask one question at a time and wait for the user\'s response."'
            ))

    def check_number_formatting(self):
        """Check for number formatting guidance."""
        prompt_lower = self.prompt.lower()

        # Check if numbers are mentioned but no formatting guidance given
        mentions_numbers = any(keyword in prompt_lower for keyword in [
            'number',
            'phone',
            'price',
            'cost',
            'amount',
            'time',
            'date'
        ])

        has_number_guidance = any(phrase in prompt_lower for phrase in [
            'spell out',
            'say "',
            'not "',
            'digit by digit'
        ])

        if mentions_numbers and not has_number_guidance:
            self.issues.append(ValidationIssue(
                severity='info',
                category='Number Formatting',
                message='Prompt mentions numbers but doesn\'t specify how to format them for voice',
                suggestion='Add guidance: "Spell out numbers (\'fifteen\' not \'15\'). Spell phone numbers digit by digit."'
            ))

    def check_tool_usage(self):
        """Check for tool usage best practices."""
        prompt_lower = self.prompt.lower()

        # Check if tools are mentioned
        has_tools = any(keyword in prompt_lower for keyword in [
            'tool',
            'function',
            'use the',
            'call ',
            'invoke'
        ])

        if has_tools:
            # Check for error handling guidance
            has_error_handling = any(phrase in prompt_lower for phrase in [
                'if.*fail',
                'error',
                'issue',
                'problem',
                'fallback'
            ])

            if not has_error_handling:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='Tool Usage',
                    message='Prompt mentions tools but lacks error handling guidance',
                    suggestion='Add: "If a tool call fails, explain the issue simply and suggest a fallback."'
                ))

            # Check for result formatting guidance
            has_result_guidance = any(phrase in prompt_lower for phrase in [
                'summarize',
                'conversational',
                'don\'t recite',
                'never recite',
                'natural language'
            ])

            if not has_result_guidance:
                self.issues.append(ValidationIssue(
                    severity='info',
                    category='Tool Usage',
                    message='Consider adding guidance on how to present tool results',
                    suggestion='Add: "Summarize tool results in conversational language. Don\'t recite technical IDs or raw data."'
                ))


def format_issues(issues: List[ValidationIssue]) -> str:
    """Format validation issues for display."""
    if not issues:
        return "✓ No issues found! Prompt follows LiveKit voice agent best practices."

    output = []

    # Group by severity
    errors = [i for i in issues if i.severity == 'error']
    warnings = [i for i in issues if i.severity == 'warning']
    info = [i for i in issues if i.severity == 'info']

    if errors:
        output.append("ERRORS (critical issues):")
        output.append("=" * 50)
        for issue in errors:
            output.append(f"\n{issue.category}: {issue.message}")
            if issue.line_number:
                output.append(f"  Line {issue.line_number}")
            if issue.suggestion:
                output.append(f"  💡 Suggestion: {issue.suggestion}")
        output.append("")

    if warnings:
        output.append("WARNINGS (recommended fixes):")
        output.append("=" * 50)
        for issue in warnings:
            output.append(f"\n{issue.category}: {issue.message}")
            if issue.line_number:
                output.append(f"  Line {issue.line_number}")
            if issue.suggestion:
                output.append(f"  💡 Suggestion: {issue.suggestion}")
        output.append("")

    if info:
        output.append("INFO (suggestions for improvement):")
        output.append("=" * 50)
        for issue in info:
            output.append(f"\n{issue.category}: {issue.message}")
            if issue.line_number:
                output.append(f"  Line {issue.line_number}")
            if issue.suggestion:
                output.append(f"  💡 Suggestion: {issue.suggestion}")
        output.append("")

    # Summary
    output.append("=" * 50)
    output.append(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")

    return '\n'.join(output)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Read prompt from file or stdin
    if sys.argv[1] == '-':
        prompt = sys.stdin.read()
        source = "stdin"
    else:
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                prompt = f.read()
            source = sys.argv[1]
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[1]}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    if not prompt.strip():
        print("Error: Prompt is empty")
        sys.exit(1)

    # Validate
    print(f"Validating LiveKit voice agent prompt from: {source}")
    print("=" * 50)
    print()

    validator = PromptValidator(prompt)
    issues = validator.validate()

    print(format_issues(issues))

    # Exit with error code if there are errors
    errors = [i for i in issues if i.severity == 'error']
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()

import streamlit as st
import re
import io  # Import io module
from difflib import SequenceMatcher

def is_line_similar(line1, line2, ratio_threshold=0.8):
    """Checks if two lines are similar based on SequenceMatcher ratio."""
    if not line1.strip() and not line2.strip(): # Consider empty lines as similar
        return True
    if not line1.strip() or not line2.strip(): # If one is empty and the other is not, not similar enough unless both are empty
        return False
    matcher = SequenceMatcher(None, line1.strip(), line2.strip())
    return matcher.ratio() >= ratio_threshold

# --- Logic Functions ---
def apply_diff_logic_smart(diff_content, original_content, filename=None):
    """
    Applies a unified diff to a string of original content with more flexible context matching.

    Args:
        diff_content (str): The content of the diff in unified format.
        original_content (str): The original content to apply the diff to.
        filename (str, optional): The filename to be patched (for diff parsing only).

    Returns:
        tuple: (success_message, warning_message, modified_content_string)
               success_message: str if successful, None otherwise
               warning_message: str if warnings occurred, None otherwise (can also be error message in case of fatal error)
               modified_content_string: str of the modified content or None if error
    """
    diff_lines = diff_content.strip().splitlines()
    if not diff_lines:
        return None, "Error: Empty diff content provided.", None, None # Return None for modified_content in error case

    target_filename = None
    hunks = []
    current_hunk = None

    # Parse the diff content
    for line in diff_lines:
        if line.startswith("+++ b/"):
            target_filename = line[6:]
            if filename and target_filename != filename:
                filename = filename
            elif not filename:
                filename = target_filename
            continue

        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = {"header": line, "lines": []}
            continue

        if current_hunk is not None:
            current_hunk["lines"].append(line)

    if current_hunk:
        hunks.append(current_hunk)

    if not filename and not target_filename:
        filename = "in-memory-content"

    original_lines = original_content.splitlines(keepends=True) if original_content else []
    original_line_index = 0
    new_lines = []
    mismatches_warnings = []  # To collect mismatch warnings

    for hunk in hunks:
        header_match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*", hunk["header"])
        if not header_match:
            return None, f"Warning: Invalid hunk header: '{hunk['header']}'. Skipping hunk.", None, None # Return None for modified_content in error case

        original_start_line = int(header_match.group(1))
        original_line_count = int(header_match.group(2)) if header_match.group(2) else 1
        modified_start_line = int(header_match.group(3))
        modified_line_count = int(header_match.group(4)) if header_match.group(4) else 1

        original_start_line -= 1  # 0-indexed

        # Copy unchanged lines before the hunk
        while original_line_index < original_start_line and original_line_index < len(original_lines):
            new_lines.append(original_lines[original_line_index])
            original_line_index += 1

        hunk_lines_index = 0
        while hunk_lines_index < len(hunk["lines"]):
            line = hunk["lines"][hunk_lines_index]

            if line.startswith(" "):  # Context line
                expected_original_line = line[1:].rstrip('\n')
                actual_original_line = original_lines[original_line_index].rstrip('\n') if original_line_index < len(original_lines) else ''

                if original_line_index < len(original_lines) and is_line_similar(actual_original_line, expected_original_line):
                    new_lines.append(original_lines[original_line_index])
                    original_line_index += 1
                else:
                    mismatches_warnings.append(f"Context line mismatch, using diff line anyway: '{line.strip()}' (Expected near line {original_start_line + 1 + hunk_lines_index}). Potential patching issue.")
                    new_lines.append(line[1:] + '\n') # Apply diff line even if context mismatch


            elif line.startswith("+"):  # Added line
                new_lines.append(line[1:] + '\n')

            elif line.startswith("-"):  # Removed line
                if original_line_index < len(original_lines) and original_lines[original_line_index].rstrip('\n') != line[1:].rstrip('\n'):
                     mismatches_warnings.append(f"Removal line context mismatch, skipping original line but applying removal from diff: '{line.strip()}' (Expected near line {original_start_line + 1 + hunk_lines_index}). Potential patching issue.")
                original_line_index += 1 # Always try to skip original line for removal, even with mismatch

            hunk_lines_index += 1

        # Copy any remaining lines after the last hunk
        while original_line_index < len(original_lines):
            new_lines.append(original_lines[original_line_index])
            original_line_index += 1

    modified_content_string = "".join(new_lines)
    if mismatches_warnings:
        warning_message = "Patch applied with potential issues:\n" + "\n".join(mismatches_warnings)
        return "Patch applied with warnings.", warning_message, modified_content_string, modified_content_string # Return modified_content also in warning case
    else:
        return "Successfully applied patch.", None, modified_content_string, modified_content_string # Return modified_content in success case


# --- Display Functions ---
def display_header():
    st.title("Diff Patch Applier (Smarter)")
    st.write("Enter your diff content and the original text content to apply the patch. This version is more tolerant to slight variations in original content.")

def display_input_fields():
    original_content = st.text_area("Original Content", height=300, placeholder="Paste the original text content here...")
    diff_content = st.text_area("Diff Content", height=300, placeholder="Paste your diff content here...")
    filename = st.text_input("Filename (Optional, for reference)", placeholder="Enter filename if needed (or extracted from diff)")
    return original_content, diff_content, filename

def display_output(success_message, warning_message, modified_content): # Removed error_message as separate argument
    if warning_message and "Error:" in warning_message: # Check if warning_message is actually an error
        st.error(warning_message)
    elif warning_message:
        st.warning(warning_message) # Display warnings in a warning box
        st.success(success_message) # Still show success message if patch applied with warnings
    elif success_message:
        st.success(success_message)

    if modified_content is not None:
        st.subheader("Modified Content:")
        st.code(modified_content, language='diff')

# --- Main Streamlit App ---
def main():
    display_header()
    original_content, diff_content, filename = display_input_fields()

    if st.button("Apply Patch (Smart)"):
        if not diff_content:
            st.error("Please provide diff content.")
        elif not original_content:
            st.error("Please provide original content to patch.")
        else:
            success_message, warning_message, modified_content, _ = apply_diff_logic_smart(diff_content, original_content, filename) # Unpack only 3, ignore the 4th return
            display_output(success_message, warning_message, modified_content) # Pass warning_message as the second argument


if __name__ == "__main__":
    main()

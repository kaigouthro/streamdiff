import streamlit as st
import re
import io  # Import io module

# --- Logic Functions ---
def apply_diff_logic(diff_content, filename=None):
    """
    Applies a unified diff to a file-like string and returns the modified content as a string.

    Args:
        diff_content (str): The content of the diff in unified format.
        filename (str, optional): The filename to be patched (for diff parsing only).

    Returns:
        tuple: (success_message, error_message, modified_content_string)
               success_message: str if successful, None otherwise
               error_message: str if error occurred, None otherwise
               modified_content_string: str of the modified content or None if error
    """
    diff_lines = diff_content.strip().splitlines()
    if not diff_lines:
        return None, "Error: Empty diff content provided.", None

    target_filename = None
    hunks = []
    current_hunk = None

    # Parse the diff content
    for line in diff_lines:
        if line.startswith("+++ b/"):
            target_filename = line[6:]  # Extract filename after "+++ b/"
            if filename and target_filename != filename:
                filename = filename # Use provided filename if available
            elif not filename:
                filename = target_filename # Use filename from diff if not provided
            continue # Skip to next line after finding target filename

        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = {"header": line, "lines": []}
            continue

        if current_hunk is not None:
            current_hunk["lines"].append(line)

    if current_hunk: # Append the last hunk
        hunks.append(current_hunk)


    if not filename and not target_filename:
        return None, "Error: No target filename found in diff or provided.", None

    original_lines = io.StringIO().readlines() # Initialize with empty lines to process diffs for empty files.
    original_line_index = 0
    new_lines = []


    for hunk in hunks:
        header_match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*", hunk["header"])
        if not header_match:
            return None, f"Warning: Invalid hunk header: '{hunk['header']}'. Skipping hunk.", None
        original_start_line = int(header_match.group(1))
        original_line_count = int(header_match.group(2)) if header_match.group(2) else 1

        modified_start_line = int(header_match.group(3))
        modified_line_count = int(header_match.group(4)) if header_match.group(4) else 1


        # Adjust original_start_line to be 0-indexed for list access
        original_start_line -= 1

        # Copy unchanged lines before the hunk
        while original_line_index < original_start_line and original_line_index < len(original_lines):
            new_lines.append(original_lines[original_line_index])
            original_line_index += 1

        hunk_line_index = 0
        while hunk_line_index < len(hunk["lines"]):
            line = hunk["lines"][hunk_line_index]

            if line.startswith(" "): # Context line - keep as is
                if original_line_index < len(original_lines) and original_lines[original_line_index].rstrip('\n') == line[1:].rstrip('\n'):
                    new_lines.append(original_lines[original_line_index])
                    original_line_index += 1
                else:
                    new_lines.append(line[1:] + '\n') # Just add the line, but warn about mismatch


            elif line.startswith("+"): # Added line
                new_lines.append(line[1:] + '\n')

            elif line.startswith("-"): # Removed line
                if original_line_index < len(original_lines) and original_lines[original_line_index].rstrip('\n') == line[1:].rstrip('\n'):
                    original_line_index += 1 # Skip original line (effectively removing it)
                else:
                    original_line_index += 1 # Skip original line, even if mismatch


            hunk_line_index += 1

    # Copy any remaining lines from the original file after the last hunk
    while original_line_index < len(original_lines):
        new_lines.append(original_lines[original_line_index])
        original_line_index += 1

    modified_content_string = "".join(new_lines)
    return "Successfully applied patch.", None, modified_content_string


# --- Display Functions ---
def display_header():
    st.title("Diff Patch Applier")
    st.write("Enter your diff content and optionally a filename to apply the patch.")

def display_input_fields():
    diff_content = st.text_area("Diff Content", height=300, placeholder="Paste your diff content here...")
    filename = st.text_input("Filename (Optional)", placeholder="Enter filename if needed (or extracted from diff)")
    return diff_content, filename

def display_output(success_message, error_message, modified_content):
    if error_message:
        st.error(error_message)
    elif success_message:
        st.success(success_message)
        if modified_content is not None:
            st.subheader("Modified Content:")
            st.code(modified_content, language='diff') # Use 'diff' language for code block


# --- Main Streamlit App ---
def main():
    display_header()
    diff_content, filename = display_input_fields()

    if st.button("Apply Patch"):
        if not diff_content:
            st.error("Please provide diff content.")
        else:
            success_message, error_message, modified_content = apply_diff_logic(diff_content, filename)
            display_output(success_message, error_message, modified_content)


if __name__ == "__main__":
    main()

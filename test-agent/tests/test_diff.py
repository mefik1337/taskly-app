from pr_test_agent.diff import parse_unified_diff

MODIFIED = """\
diff --git a/backend/app/features/todos/repository.py b/backend/app/features/todos/repository.py
index 1111111..2222222 100644
--- a/backend/app/features/todos/repository.py
+++ b/backend/app/features/todos/repository.py
@@ -14,0 +15,3 @@ class TodoRepository:
+    def count(self) -> int:
+        statement = select(func.count(TodoRecord.id))
+        return self.session.scalar(statement)
@@ -30 +33 @@ class TodoRepository:
-        return None
+        return False
"""


def test_modified_file_reports_new_side_line_numbers_of_every_hunk():
    [change] = parse_unified_diff(MODIFIED)
    assert change.path == "backend/app/features/todos/repository.py"
    assert change.status == "modified"
    assert change.added_lines == [15, 16, 17, 33]

LIFECYCLE = """\
diff --git a/frontend/src/lib/dates.ts b/frontend/src/lib/dates.ts
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/frontend/src/lib/dates.ts
@@ -0,0 +1,2 @@
+export const today = () => new Date()
+export const epoch = () => new Date(0)
diff --git a/frontend/src/lib/legacy.ts b/frontend/src/lib/legacy.ts
deleted file mode 100644
index 4444444..0000000
--- a/frontend/src/lib/legacy.ts
+++ /dev/null
@@ -1 +0,0 @@
-export const legacy = true
diff --git a/backend/app/old_name.py b/backend/app/new_name.py
similarity index 90%
rename from backend/app/old_name.py
rename to backend/app/new_name.py
index 5555555..6666666 100644
--- a/backend/app/old_name.py
+++ b/backend/app/new_name.py
@@ -3 +3 @@
-VALUE = 1
+VALUE = 2
"""


def test_added_deleted_and_renamed_files_keep_their_lifecycle_status():
    added, deleted, renamed = parse_unified_diff(LIFECYCLE)
    assert (added.path, added.status, added.added_lines) == ("frontend/src/lib/dates.ts", "added", [1, 2])
    assert (deleted.path, deleted.status, deleted.added_lines) == ("frontend/src/lib/legacy.ts", "deleted", [])
    assert (renamed.path, renamed.status, renamed.added_lines) == ("backend/app/new_name.py", "renamed", [3])
    assert renamed.previous_path == "backend/app/old_name.py"

AMBIGUOUS_CONTENT = """\
diff --git a/frontend/src/lib/counter.ts b/frontend/src/lib/counter.ts
index 7777777..8888888 100644
--- a/frontend/src/lib/counter.ts
+++ b/frontend/src/lib/counter.ts
@@ -4,2 +4,3 @@ export function next() {
---- removed line starting with dashes
+++ added line starting with pluses
 unchanged
+tail
"""


def test_hunk_lines_that_look_like_file_headers_are_counted_as_content():
    [change] = parse_unified_diff(AMBIGUOUS_CONTENT)
    assert change.path == "frontend/src/lib/counter.ts"
    assert change.added_lines == [4, 6]

WITHOUT_HUNKS = """\
diff --git a/frontend/src/lib/old.ts b/frontend/src/lib/renamed.ts
similarity index 100%
rename from frontend/src/lib/old.ts
rename to frontend/src/lib/renamed.ts
diff --git a/frontend/public/logo.png b/frontend/public/logo.png
new file mode 100644
index 0000000..9999999
Binary files /dev/null and b/frontend/public/logo.png differ
"""


def test_files_without_hunks_still_report_their_path():
    renamed, binary = parse_unified_diff(WITHOUT_HUNKS)
    assert (renamed.path, renamed.status, renamed.added_lines) == ("frontend/src/lib/renamed.ts", "renamed", [])
    assert (binary.path, binary.status, binary.added_lines) == ("frontend/public/logo.png", "added", [])

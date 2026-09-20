/* Libry UI messages — English (en).
   Format contract: the assigned object must be strict JSON (double-quoted keys,
   no trailing commas, no comments) — tests/test_i18n.py relies on it to verify
   key parity across locales. See docs/frontend-style.md to add a language. */
window.LibryLocales = window.LibryLocales || {};
window.LibryLocales["en"] = {
  "_meta": { "name": "English" },
  "app": { "title": "Libry", "brand": "Libry", "logoAlt": "Libry logo" },
  "common": {
    "loading": "Loading…",
    "back": "← Back",
    "logout": "Sign out",
    "close": "Close",
    "save": "Save",
    "never": "Never",
    "admin": "Admin",
    "personal": "Personal",
    "personalTitle": "Personal document",
    "personalWithTitle": "Personal · Owner: {owner}",
    "language": "Language"
  },
  "login": {
    "username": "Username",
    "password": "Password",
    "submit": "Sign in",
    "submitting": "Signing in…"
  },
  "settings": { "title": "Settings" },
  "pw": { "show": "Show password", "hide": "Hide password" },
  "pwChange": {
    "title": "Change Password",
    "oldPlaceholder": "Current password",
    "newPlaceholder": "New password (at least 8 characters)",
    "confirmPlaceholder": "Confirm new password",
    "submit": "Update",
    "submitting": "Saving…",
    "ok": "Password updated. It takes effect the next time you sign in.",
    "tooShort": "New password must be at least 8 characters",
    "mismatch": "The two new passwords do not match"
  },
  "users": {
    "title": "Accounts",
    "delete": "Delete",
    "namePlaceholder": "New username",
    "passwordPlaceholder": "Password (at least 8 characters)",
    "add": "Add account",
    "adding": "Adding…",
    "nameRequired": "Please enter a username",
    "passwordShort": "Password must be at least 8 characters",
    "deleteConfirm": "Delete user \"{name}\"? Their reading state is kept, but they can no longer sign in."
  },
  "sync": {
    "title": "Data Sync",
    "desc": "Syncs accounts, read history and bookmarks to GitHub, and merges both ways between this machine and the VPS.",
    "lastRun": "Last sync: {ts} ({result})",
    "trigger": "Sync now",
    "syncing": "Syncing…",
    "started": "Data sync triggered"
  },
  "syncResult": {
    "pushed": "Pushed",
    "no changes": "No changes",
    "dry-run": "Dry run",
    "skipped": "Skipped",
    "error": "Failed"
  },
  "purge": {
    "title": "Pages Marked for Deletion",
    "desc": "Pages marked with the delete icon in the reader are batch-deleted on the next scheduled ingest, cleaning references from other pages as well. You can also run the purge now.",
    "empty": "No pages marked for deletion",
    "stale": "Stale",
    "staleTitle": "File no longer exists in the vault; the mark will simply be reconciled at purge time",
    "unmark": "Unmark for deletion",
    "lastRun": "Last purge: {ts} ({result})",
    "execute": "Delete now ({n})",
    "running": "Running…",
    "done": "Purge completed",
    "failed": "Purge failed",
    "okSummary": "Deleted {pages} page(s), cleaned {refs} reference(s)",
    "confirm": "Delete these {n} marked pages now?\nThe files will be deleted and references from other pages cleaned. Changes are committed and pushed to GitHub — this cannot be undone."
  },
  "purgeResult": { "ok": "Completed", "empty": "Nothing to delete", "error": "Failed" },
  "doc": {
    "dates": "Created {created} · Updated {updated}",
    "markedBanner": "This page is marked for deletion and will be removed on the next scheduled purge, along with references from other pages.",
    "bookmark": "Bookmark",
    "unbookmark": "Remove bookmark",
    "markUnread": "Mark as unread",
    "markRead": "Mark as read",
    "setShared": "Make shared",
    "setPersonal": "Make personal",
    "markDelete": "Mark for deletion",
    "markedBadge": "Marked for deletion",
    "markConfirm": "Marking this page will delete it on the next scheduled purge, along with references from other pages. Mark it?",
    "relatedTitle": "Related pages",
    "relOpen": "Show graph",
    "relClose": "Hide graph",
    "toc": "Contents",
    "nowPersonal": "Document is now personal",
    "nowShared": "Document is now shared",
    "markedToast": "Marked for deletion",
    "unmarkedToast": "Delete mark removed"
  },
  "bm": {
    "title": "Bookmarks",
    "all": "All",
    "empty": "No bookmarks yet — tap the bookmark icon on an article to add one",
    "addedAt": "Bookmarked {date}",
    "editTags": "Edit tags",
    "remove": "Remove bookmark",
    "removedToast": "Bookmark removed",
    "tagsSaved": "Tags saved"
  },
  "bmEditor": {
    "title": "Bookmark tags",
    "removeTag": "Remove tag",
    "placeholder": "Type a tag, then press Enter or comma to add",
    "suggest": "Suggested tags"
  },
  "graph": {
    "title": "Knowledge Graph",
    "searchPlaceholder": "Find a node (Enter)…",
    "allTags": "All tags",
    "notFound": "No matching node",
    "emptyPre": "Graph data has not been generated. Run",
    "emptyPost": "locally, then publish and sync.",
    "tooltip": "{title} ({type})"
  },
  "list": {
    "searchPlaceholder": "Search titles / summaries…",
    "filter": "Filters",
    "empty": "No matching documents",
    "loadMore": "Load more ({n}/{total})",
    "whoami": "Signed in as {name}",
    "filterTag": "Filter by tag: {tag}"
  },
  "status": { "all": "All", "new": "New", "unread": "Unread", "read": "Read" },
  "filters": {
    "allTypes": "All types",
    "allVisibility": "All visibility",
    "byVisibility": "Filter by personal/shared",
    "shared": "Shared",
    "dateFrom": "Created from",
    "dateTo": "Created to",
    "sortCreated": "By created time",
    "sortUpdated": "By updated time",
    "sortTitle": "By title",
    "clear": "Clear filters"
  },
  "type": { "sources": "Sources", "entities": "Entities", "concepts": "Concepts", "synthesis": "Synthesis", "archive": "Archive" },
  "err": {
    "requestFailed": "Request failed ({status})",
    "invalidCredentials": "Incorrect username or password",
    "adminRequired": "Administrator access required"
  },
  "api": {
    "rate_limited": "Too many attempts. Please try again later.",
    "invalid_credentials": "Incorrect username or password",
    "current_password_wrong": "Current password is incorrect",
    "password_too_short": "Password must be at least 8 characters",
    "doc_not_found": "Document not found",
    "file_not_found": "File not found",
    "files_not_list": "files must be an array",
    "not_bookmarked": "This document is not bookmarked",
    "bad_visibility": "visibility must be shared or personal",
    "invalid_sync_secret": "Invalid X-Sync-Secret",
    "user_not_found": "User not found",
    "bad_username": "Username may only contain letters, digits, - _ .",
    "user_exists": "Username already exists",
    "cannot_delete_self": "Cannot delete the account you are signed in with",
    "cannot_delete_last_admin": "Cannot delete the only administrator",
    "auth_required": "Not signed in, or the session has expired",
    "admin_required": "Administrator access required"
  }
};

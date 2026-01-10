# Import deploy module early to ensure transform patching runs
# This ensures filename-aware transforms are available for all tasks
import tasks.deploy

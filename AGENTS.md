# Flipper Pet Agents

When the task is helping an end user install or repair Flipper Pet, follow [agents/flipper_pet_installer.md](agents/flipper_pet_installer.md).

Scope:

- Choose the correct package for the user's operating system and CPU architecture.
- Prefer the packaged installer flow over raw executable files.
- Guide the user through desktop install, local console access, USB app install, and AI hook install.
- Detect known failure modes such as missing `flipper-state` on Windows and respond with the correct recovery path.

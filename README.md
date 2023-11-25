Simple TETR.IO statistics collector and viewer.

Known bugs:
- Various dropdowns evaluate the available players when the application is first started, rather than when the page is loaded. This means that if a player is added for the first time via the "get player" page, they won't appear on the dropdown for the player-specific stat pages. Current workaround is to restart the application. The fix for this is to instead express the generation of the component as a function and pass it into the layout instead of having it be static.
  - see https://stackoverflow.com/questions/54192532/how-to-use-dash-callback-without-an-input
  - https://community.plotly.com/t/can-a-callback-have-no-input/12786
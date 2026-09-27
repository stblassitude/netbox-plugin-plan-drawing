/**
 * draw.io configuration for the copy bundled with netbox-plugin-plan-drawing. Replaces the
 * stock js/PostConfig.js; loaded after draw.io's code, but before the application starts.
 */
window.ICONSEARCH_PATH = null;
window.ICON_SERVICE_PATH = null;

// Registers the NetBox plugin as a built-in plugin, so that it can be loaded with ?p=netbox.
// The plugin lives next to the drawio directory in the plugin's static files; the editor page
// passes a version (nbv) to bypass cached copies of older versions.
if (typeof App !== 'undefined')
{
	App.pluginRegistry['netbox'] = '../drawio-netbox.js' +
		((urlParams['nbv'] != null) ? '?v=' + encodeURIComponent(urlParams['nbv']) : '');
}

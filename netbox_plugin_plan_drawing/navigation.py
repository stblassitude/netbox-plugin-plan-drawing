from netbox.choices import ButtonColorChoices
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label='Plan Drawings',
    icon_class='mdi mdi-floor-plan',
    groups=(
        ('Plan Drawings', (
            PluginMenuItem(
                link='plugins:netbox_plugin_plan_drawing:plandrawing_list',
                link_text='Drawings',
                permissions=('netbox_plugin_plan_drawing.view_plandrawing',),
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_plugin_plan_drawing:plandrawing_add',
                        title='Add',
                        icon_class='mdi mdi-plus-thick',
                        color=ButtonColorChoices.GREEN,
                        permissions=('netbox_plugin_plan_drawing.add_plandrawing',),
                    ),
                ),
            ),
        )),
    ),
)

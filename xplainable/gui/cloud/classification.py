import xplainable
from ..cloud.classification import XClassifier
from ...utils import TrainButton, ping_server
from  ...quality import XScan
from ...utils.xwidgets import TextInput
from ...utils.api import get_response_content

from IPython.display import display, clear_output
import ipywidgets as widgets

def classifier(df):
    """ Trains an xplainable classifier via a simple GUI.

    Args:
        df (pandas.DataFrame): Training data including target
        model_name (str): A unique name for the model
        hostname (str): Base url of host machine

    Raises:
        RuntimeError: When model fails to fit

    Returns:
        xplainale.models.XClassifier: The trained model
    """

    # This allows widgets to show full label text
    style = {'description_width': 'initial'}

    # Instantiate widget output
    outt = widgets.Output()

    # Instantiate the model
    model = XClassifier(model_name='', model_description='')

    # HEADER
    model_name = TextInput(
        label="Model name: ",
        label_type='h5',
        label_margin='2px 10px 0 0',
        box_width='220px')

    model_description = TextInput(
        label="Model description: ",
        label_type='h5',
        label_margin='2px 10px 0 15px',
        box_width='350px'
        )

    model_details = widgets.HBox([model_name(), model_description()])
    loader_dropdown = widgets.Dropdown(options=[None])
    description_output = widgets.HTML(
        f'', layout=widgets.Layout(margin='0 0 0 15px'))

    loader = widgets.HBox(
        [loader_dropdown, description_output],
        layout=widgets.Layout(display='none'))

    buttons = widgets.ToggleButtons(options=['New Model', 'Existing Model'])
    buttons.layout = widgets.Layout(margin="0 0 20px 0")

    class Options:
        options = []
    
    model_options = Options()

    def get_models():
        models_response = xplainable.client.__session__.get(
            f'{xplainable.client.hostname}/v1/models'
        )
        
        models = get_response_content(models_response)
        
        model_options.options = [
            (i['model_name'], i['model_description']) for i in models if \
                i['model_type'] == 'binary_classification']

        loader_dropdown.options = [None]+[i['model_name'] for i in models]

    def on_select(_):
        if buttons.index == 1:
            model_name.hide()
            model_description.hide()
            loader_dropdown.index = 0
            loader.layout.display = 'flex'
            get_models()
            model_name.value = ''
            model_description.value = ''
        else:
            loader.layout.display = 'none'
            model_name.value = ''
            model_description.value = ''
            model_name.show()
            model_description.show()
            
    def model_selected(_):
        idx = loader_dropdown.index
        if idx is None:
            model_name.value = ''
            description_output.value = ''
            model_description.value = ''
        elif len(model_options.options) > 0:
            model_name.value = model_options.options[idx-1][0]
            desc = model_options.options[idx-1][1]
            description_output.value = f'{desc}'
            model_description.value = desc

    buttons.observe(on_select, names=['value'])
    loader_dropdown.observe(model_selected, names=['value'])

    divider = widgets.HTML(
        f'<hr class="solid">', layout=widgets.Layout(height='auto'))

    connection_status = widgets.HTML(f"<h5><font color='red'>[offline]</h5>")
    connection_status.layout = widgets.Layout(margin='10px 0 0 0')

    connection_status_button = widgets.Button(description="offline")

    connection_status_button.layout = widgets.Layout(
        height='25px', width='80px', margin='0 0 0 10px')

    connection_status_button.style = {
            "button_color": '#e21c47',
            "text_color": 'white',
            "font_size": "11.5px"
            }

    machines = xplainable.client.machines
    machines_dropdown = widgets.Dropdown(options=machines.keys())
    machines_dropdown.layout = widgets.Layout(width='200px', margin='0 0 0 20px')

    def on_machine_change(_):
        machine_id = machines[machines_dropdown.value]
        xplainable.client.__session__.params.update({'machine_id': machine_id})

    def _check_connection(_):
        try:
            if ping_server(xplainable.client.hostname):
                connection_status_button.description = "Connected"
                connection_status_button.style.button_color = '#12b980'
            else:
                connection_status_button.description = "Offline"
                connection_status_button.style.button_color = '#e21c47'
        except:
            pass
        
    machines_dropdown.observe(on_machine_change, names=['value'])
    machines_dropdown.observe(_check_connection, names=['value'])
            
    button_display = widgets.HBox(
        [buttons, machines_dropdown, connection_status_button])

    header = widgets.VBox([button_display, model_details, loader, divider])
    header.layout = widgets.Layout(margin='0 0 20px 0')

    # COLUMN 1
    col1a = widgets.HTML(
        f"<h5>Target</h5>", layout=widgets.Layout(height='auto'))

    id_title = widgets.HTML(f"<h5>ID Column (0 selected)</h5>")

    possible_targets = [None] + [i for i in df.columns if df[i].nunique() < 20]
    
    target = widgets.Dropdown(
        options=possible_targets,
        layout = widgets.Layout(width='200px')
        )

    possible_partitions = [None]+[i for i in df.columns if df[i].nunique() < 11]

    partition_on = widgets.Dropdown(
        options=possible_partitions,
        layout = widgets.Layout(width='200px')
        )

    # get all cols with cardinality of 1
    potential_id_cols = [None] + [
        col for col in df.columns if XScan._cardinality(df[col]) == 1]

    id_columns = widgets.SelectMultiple(
        options=potential_id_cols,
        style=style,
        layout = widgets.Layout(width='200px')
        )

    colA = widgets.VBox([col1a, target, id_title, id_columns])
    colA.layout = widgets.Layout(margin='0 0 0 15px')

    # COLUMN 2
    # Options to toggle param/opt view
    options = {
        True: 'flex',
        False: 'none'
    }

    # Change view on optimisation button change
    def optimise_changed(_):
        vala = optimise.value
        valb = not vala

        opt_params.layout.display = options[vala]
        std_params.layout.display = options[valb]
        optimise_metric.layout.display = options[vala]

    def target_changed(_):

        if target.value is None:
            train_button.disabled = True
        else:
            train_button.disabled = False

    optimise = widgets.Dropdown(
        value=False, options=[True, False],
        description='optimise:', style=style,
        layout = widgets.Layout(max_width='200px'))

    optimise_metrics = [
        'weighted-f1',
        'macro-f1',
        'accuracy',
        'recall',
        'precision'
    ]

    optimise_metric = widgets.Dropdown(
        value='weighted-f1',
        options=optimise_metrics,
        description='metric:',
        style=style,
        layout = widgets.Layout(max_width='200px', margin='0 0 0 10px'))

    # Hide on instantiation
    optimise_metric.layout.display = 'none'

    optimise_display = widgets.HBox([
        optimise,
        optimise_metric
    ])

    optimise.observe(optimise_changed, names=['value'])
    target.observe(target_changed, names=['value'])

    # Param pickers
    max_depth = widgets.IntSlider(
        value=12, min=2, max=100, step=1, description='max_depth:',
        style=style)

    min_leaf_size = widgets.FloatSlider(
        value=0.015, min=0.001, max=0.2, step=0.001, readout_format='.3f',
        description='min_leaf_size:', style=style)

    min_info_gain = widgets.FloatSlider(
        value=0.015, min=0.001, max=0.2, step=0.001, readout_format='.3f',
        description='min_info_gain:', style=style)
    
    # Optimise param pickers
    n_trials = widgets.IntSlider(
        value=30, min=5, max=150, step=5, description='n_trials:',
        style=style)

    early_stopping = widgets.IntSlider(
        value=15, min=5, max=50, step=5, description='early_stopping:',
        style=style)

    # SEARCH SPACE – MAX_DEPTH
    max_depth_space = widgets.IntRangeSlider(
        value=[4, 22],
        min=2,
        max=100,
        step=1,
        description="max_depth:",
        style={'description_width': 'initial'},
        layout = widgets.Layout(min_width='350px')
    )

    max_depth_step = widgets.Dropdown(
        options=[1, 2, 5],
        layout = widgets.Layout(max_width='75px')
    )

    max_depth_space_display = widgets.HBox([max_depth_space, max_depth_step])

    # SEARCH SPACE – MIN_LEAF_SIZE
    min_leaf_size_space = widgets.FloatRangeSlider(
        value=[0.005, 0.08],
        min=0.005,
        max=0.2,
        step=0.005,
        description="min_leaf_size:",
        style={'description_width': 'initial'},
        readout_format='.3f',
        layout = widgets.Layout(min_width='350px')
    )

    min_leaf_size_step = widgets.Dropdown(
        options=[0.005, 0.01, 0.02],
        layout = widgets.Layout(max_width='75px')
    )

    min_leaf_size_display = widgets.HBox(
        [min_leaf_size_space, min_leaf_size_step])

    # SEARCH SPACE – MIN_LEAF_SIZE
    min_info_gain_space = widgets.FloatRangeSlider(
        value=[0.005, 0.08],
        min=0.005,
        max=0.2,
        step=0.005,
        description="min_info_gain:",
        style={'description_width': 'initial'},
        readout_format='.3f',
        layout = widgets.Layout(min_width='350px')
    )

    min_info_gain_step = widgets.Dropdown(
        options=[0.005, 0.01, 0.02],
        layout = widgets.Layout(max_width='75px')
    )

    min_info_gain_display = widgets.HBox(
        [min_info_gain_space, min_info_gain_step])

    std_params = widgets.VBox([
        widgets.HTML(f"<h5>Hyperparameters</h5>"),
        max_depth,
        min_leaf_size,
        min_info_gain
    ])

    opt_params = widgets.VBox([
        widgets.HTML(f"<h5>Trials</h5>"),
        n_trials,
        early_stopping,
        widgets.HTML(f"<h5>Search Space</h5>"),
        max_depth_space_display,
        min_leaf_size_display,
        min_info_gain_display
    ])

     # Set initial optimise widgets to no display
    opt_params.layout.display = 'none'

    colBParams = widgets.VBox([
        optimise_display,
        std_params,
        opt_params
        ])

    partition_header = widgets.HTML(f"<h5>Partition on</h5>")

    alpha_header = widgets.HTML(f"<h5>bin_alpha</h5>")
    bin_alpha = widgets.FloatSlider(value=0.05, min=0.01, max=0.5, step=0.01)

    validation_size_header = widgets.HTML(f"<h5>Validation Size</h5>")
    validation_size = widgets.FloatSlider(
        value=0.2, min=0.05, max=0.5, step=0.01)

    colBSettings = widgets.VBox([
        partition_header,
        partition_on,
        alpha_header,
        bin_alpha,
        validation_size_header,
        validation_size
        ])

    colB = widgets.Tab([colBParams, colBSettings])
    colB.set_title(0, 'Parameters')
    colB.set_title(1, 'Settings')
    colB.layout = widgets.Layout(margin='0 0 0 15px', min_width='400px')
    
    body = widgets.HBox([colA, colB])

    # FOOTER
    train_button = TrainButton(
        description='Train Model', model=model, icon='bolt', disabled=True)

    close_button = widgets.Button(description='Close')

    train_button.layout = widgets.Layout(margin=' 10px 0 10px 20px')
    close_button.layout = widgets.Layout(margin=' 10px 0 10px 10px')

    footer = widgets.VBox(
        [divider, widgets.HBox([train_button, close_button])])

    # SCREEN – Build final screen
    screen = widgets.VBox([header, body, footer, outt])
    
    # Close screen
    def close():
        header.close()
        body.close()
        footer.close()

    # Close and clear
    def close_button_click(_):
        close()
        clear_output()

    def id_cols_changed(_):
        id_vals = [i for i in list(id_columns.value) if i is not None]
        id_title.value = f"<h5>ID Column ({len(id_vals)} selected)</h5>"

    # Train model on click
    def train_button_clicked(b):
        model_description.disable()
        model_name.disable()
        loader_dropdown.disabled = True
        buttons.disabled = True

        with outt:
        
            model = b.model
            model.model_name = model_name.value
            model.model_description = model_description.value
            model.partition_on = partition_on.value
            model.max_depth = max_depth.value
            model.min_leaf_size = min_leaf_size.value
            model.min_info_gain = min_info_gain.value
            model.bin_alpha = bin_alpha.value
            model.optimise = optimise.value
            model.n_trials = n_trials.value
            model.early_stopping = early_stopping.value
            model.validation_size = validation_size.value
            model.max_depth_space = list(max_depth_space.value) + \
                [max_depth_step.value]

            model.min_leaf_size_space = list(min_leaf_size_space.value) + \
                [min_leaf_size_step.value]

            model.min_info_gain_space = list(min_info_gain_space.value) + \
                [min_info_gain_step.value]

            model.opt_metric = optimise_metric.value

            try:
                body.close()
                footer.close()
                
                X, y = df.drop(columns=[target.value]), df[target.value]

                id_cols = [i for i in list(id_columns.value) if i is not None]
                model.fit(X, y, id_columns=id_cols)

            except Exception as e:
                close()
                clear_output()
                raise RuntimeError(e)

    # Listen for clicks
    train_button.on_click(train_button_clicked)
    train_button.style = {
            "button_color": '#0080ea',
            "text_color": 'white'
            }
            
    close_button.on_click(close_button_click)
    connection_status_button.on_click(_check_connection)

    # Listen for changes
    id_columns.observe(id_cols_changed, names=['value'])

    # Display screen
    display(screen)

    # Ping server to check for connection
    _check_connection(xplainable.client.hostname)

    # Need to return empty model first
    return model
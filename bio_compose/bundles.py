# File for housing methods that edit and create common composition bundles such as ODE/FBA, Particle(stochastic)/PDE, etc
from typing import * 


class BioBundle:
    def generate_port_spec(self, port_params: Union[Dict[str, str], List[str]]):
        port = {}
        if isinstance(port_params, list):
            for port_name in port_params:
                port[port_name] = [f'{port_name}_store']
        else:
            for port_name, store_name in port_params.items():
                port[port_name] = [store_name]
        
        return port 
    
    def generate_node(
            self, 
            composition: Dict[str, Dict[str, Any]],
            node_name: str, 
            node_type: str, 
            address: str, 
            config: Dict[str, Any], 
            input_ports: Optional[Union[Dict[str, str], List[str]]] = None, 
            output_ports: Optional[Union[Dict[str, str], List[str]]] = None
            ) -> Dict:
        inputs = self.generate_port_spec(input_ports) if input_ports else {}
        outputs = self.generate_port_spec(output_ports) if output_ports else {}

        # add the new node to the composition
        composition[node_name] = {
            '_type': node_type,
            'address': address,
            'config': config,
            'inputs': inputs,
            'outputs': outputs
        }
        
        return composition
    
    def add_emitter_node(self, composition: Dict[str, Dict[str, Any]], emitter_address_id: str, emitted_schema: Dict[str, str], memory_stores: List[str]):
        emit_config = {'emit': emitted_schema}
        input_port_spec = {}
        for i, dataname in enumerate(list(emitted_schema.keys())):
            input_port_spec[dataname] = memory_stores[i]

        return self.generate_node(composition=composition, node_type='step', node_name=emitter_address_id, address=f'local:{emitter_address_id}', config=emit_config, input_ports=input_port_spec)
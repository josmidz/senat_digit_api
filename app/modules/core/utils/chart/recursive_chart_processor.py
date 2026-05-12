"""
Recursive Chart Processor Utility

This utility provides recursive processing capabilities for hierarchical chart data structures.
It can handle nested children and apply transformations at each level.
"""

from typing import Any, Dict, List, Callable, Optional, Awaitable
import asyncio


class RecursiveChartProcessor:
    """Utility class for processing hierarchical chart data with recursive logic."""
    
    @staticmethod
    async def process_chart_with_counts(
        chart_data: List[Dict[str, Any]], 
        count_callback: Callable[[str], Awaitable[Dict[str, int]]],
        id_extractor: Callable[[Dict[str, Any]], str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process chart data recursively, adding counts to each node.
        
        Args:
            chart_data: List of chart elements with potential children
            count_callback: Async function that takes an ID and returns count data
            id_extractor: Function to extract ID from element (optional)
            
        Returns:
            Processed chart data with counts added to each node
        """
        
        async def process_element(element: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively process a single chart element."""
            
            # Extract element ID
            if id_extractor:
                element_id = id_extractor(element)
            else:
                # Default ID extraction logic
                if isinstance(element.get('id'), dict):
                    element_id = element['id'].get('display_value', element['id'])
                else:
                    element_id = element.get('id')
            
            # Get counts for current element
            counts = await count_callback(element_id) if element_id else {}
            
            # Process children recursively if they exist
            processed_children = []
            if 'children' in element and element['children']:
                for child in element['children']:
                    processed_child = await process_element(child)
                    processed_children.append(processed_child)
            
            # Return processed element with counts and processed children
            return {
                **element,
                **counts,
                "children": processed_children
            }
        
        # Process all root elements
        processed_data = []
        for element in chart_data:
            processed_element = await process_element(element)
            processed_data.append(processed_element)
        
        return processed_data
    
    @staticmethod
    async def process_chart_with_transformation(
        chart_data: List[Dict[str, Any]], 
        transform_callback: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        children_key: str = "children"
    ) -> List[Dict[str, Any]]:
        """
        Process chart data recursively, applying transformation to each node.
        
        Args:
            chart_data: List of chart elements with potential children
            transform_callback: Async function that transforms each element
            children_key: Key name for children array (default: "children")
            
        Returns:
            Processed chart data with transformations applied to each node
        """
        
        async def process_element(element: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively process and transform a single chart element."""
            
            # Apply transformation to current element
            transformed_element = await transform_callback(element.copy())
            
            # Process children recursively if they exist
            if children_key in element and element[children_key]:
                processed_children = []
                for child in element[children_key]:
                    processed_child = await process_element(child)
                    processed_children.append(processed_child)
                transformed_element[children_key] = processed_children
            
            return transformed_element
        
        # Process all root elements
        processed_data = []
        for element in chart_data:
            processed_element = await process_element(element)
            processed_data.append(processed_element)
        
        return processed_data
    
    @staticmethod
    def flatten_chart_data(
        chart_data: List[Dict[str, Any]], 
        children_key: str = "children",
        include_level: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Flatten hierarchical chart data into a flat list.
        
        Args:
            chart_data: List of chart elements with potential children
            children_key: Key name for children array (default: "children")
            include_level: Whether to include level information
            
        Returns:
            Flattened list of all chart elements
        """
        
        def flatten_element(element: Dict[str, Any], level: int = 0) -> List[Dict[str, Any]]:
            """Recursively flatten a single chart element."""
            
            # Create a copy of the element without children
            flattened_element = {k: v for k, v in element.items() if k != children_key}
            
            if include_level:
                flattened_element['level'] = level
            
            result = [flattened_element]
            
            # Process children recursively if they exist
            if children_key in element and element[children_key]:
                for child in element[children_key]:
                    result.extend(flatten_element(child, level + 1))
            
            return result
        
        # Flatten all root elements
        flattened_data = []
        for element in chart_data:
            flattened_data.extend(flatten_element(element))
        
        return flattened_data
    
    @staticmethod
    def count_total_nodes(
        chart_data: List[Dict[str, Any]], 
        children_key: str = "children"
    ) -> int:
        """
        Count total number of nodes in hierarchical chart data.
        
        Args:
            chart_data: List of chart elements with potential children
            children_key: Key name for children array (default: "children")
            
        Returns:
            Total count of all nodes
        """
        
        def count_element(element: Dict[str, Any]) -> int:
            """Recursively count nodes in a single chart element."""
            count = 1  # Count current element
            
            # Count children recursively if they exist
            if children_key in element and element[children_key]:
                for child in element[children_key]:
                    count += count_element(child)
            
            return count
        
        # Count all root elements
        total_count = 0
        for element in chart_data:
            total_count += count_element(element)
        
        return total_count
    
    @staticmethod
    def find_node_by_id(
        chart_data: List[Dict[str, Any]], 
        target_id: str,
        id_key: str = "id",
        children_key: str = "children"
    ) -> Optional[Dict[str, Any]]:
        """
        Find a specific node by ID in hierarchical chart data.
        
        Args:
            chart_data: List of chart elements with potential children
            target_id: ID to search for
            id_key: Key name for ID field (default: "id")
            children_key: Key name for children array (default: "children")
            
        Returns:
            Found node or None if not found
        """
        
        def search_element(element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Recursively search for target ID in a single chart element."""
            
            # Check current element
            element_id = element.get(id_key)
            if isinstance(element_id, dict):
                element_id = element_id.get('display_value', element_id)
            
            if str(element_id) == str(target_id):
                return element
            
            # Search children recursively if they exist
            if children_key in element and element[children_key]:
                for child in element[children_key]:
                    found = search_element(child)
                    if found:
                        return found
            
            return None
        
        # Search all root elements
        for element in chart_data:
            found = search_element(element)
            if found:
                return found
        
        return None


# Convenience functions for common use cases
async def process_org_chart_with_counts(
    chart_data: List[Dict[str, Any]], 
    count_callback: Callable[[str], Awaitable[Dict[str, int]]]
) -> List[Dict[str, Any]]:
    """Convenience function for processing organizational charts with counts."""
    return await RecursiveChartProcessor.process_chart_with_counts(chart_data, count_callback)


def flatten_org_chart(chart_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function for flattening organizational charts."""
    return RecursiveChartProcessor.flatten_chart_data(chart_data, include_level=True)

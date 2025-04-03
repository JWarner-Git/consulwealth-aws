# ConsulWealth Clean Backend Development Ruleset

This document outlines the development guidelines and best practices for maintaining a clean, consistent, and maintainable codebase for the ConsulWealth project.

## Directory and File Structure
1. **App-based Organization**: Keep related functionality in dedicated Django apps
2. **Consistent Naming**: Use snake_case for files and directories
3. **Logical Grouping**: Group related views, models, and templates together
4. **Init Files**: Ensure `__init__.py` files are present where needed for proper Python module imports

## Templates
1. **Inheritance Hierarchy**: Strictly follow the template inheritance pattern:
   - `base.html` → `base_dashboard.html` → specific page templates
2. **Block Consistency**: Use consistent block names across templates
3. **Page-specific CSS**: Include in dedicated blocks rather than directly in HTML
4. **Template Tags**: Store in proper app-level `templatetags` directories, not in general templates folder

## CSS and Styling
1. **CSS Variables**: Use the established variable system (`--primary-color`, etc.) for all styling
2. **Centralized Files**: Keep styles in dedicated CSS files, not inline
3. **Mobile Responsiveness**: Ensure all templates include responsive design
4. **Selector Specificity**: Avoid overly specific selectors that are hard to override
5. **Bootstrap Integration**: Use Bootstrap classes when possible, customize only when necessary

## JavaScript
1. **Module Pattern**: Use modern JS practices (modules, namespaces)
2. **Event Handling**: Consistent approach to DOM events
3. **Library Management**: Document external dependencies clearly
4. **Async Operations**: Handle errors properly in all async operations

## Database and Models
1. **Model Organization**: One logical model per file
2. **Field Naming**: Use descriptive, consistent field names
3. **Relationships**: Clearly document relationships between models
4. **Migration Management**: Keep migrations organized and tested
5. **Shadow User Pattern**: Maintain the established pattern of shadow Django users for Supabase

## Views and API Endpoints
1. **View Organization**: Group related views in dedicated modules
2. **Decorator Usage**: Consistent use of authentication decorators
3. **Error Handling**: Comprehensive error handling in all views
4. **Response Formats**: Consistent response formats for all API endpoints

## Authentication and Authorization
1. **Supabase Integration**: Follow established patterns for Supabase auth
2. **Permission Checks**: Consistent permission validation
3. **Token Management**: Proper handling of auth tokens

## Code Quality
1. **Documentation**: Docstrings for all functions, classes, and modules
2. **Logging**: Consistent logging throughout the application
3. **Type Hints**: Use type hints for better code clarity
4. **Testing**: Write tests for critical functionality

## Specific to This Project
1. **Dashboard Layout**: Maintain the full-width layout we've established
2. **Color Scheme**: Use the established color variables consistently
3. **Card Design**: Maintain consistency in card styling across all pages
4. **Sidebar**: Keep consistent sidebar navigation

## Development Workflow
1. **Feature Branches**: Develop new features in dedicated branches
2. **Code Reviews**: Review code before merging to main branches
3. **Incremental Changes**: Make small, focused changes rather than large rewrites
4. **Testing Strategy**: Test changes thoroughly before deployment

## Visual Design Guidelines

### Color Palette
- **Primary Dark**: `#2B5830` (Dark green from logo)
- **Primary Medium**: `#4D8B48` (Medium green)
- **Primary Light**: `#8CC63F` (Light green/lime)
- **Accent Green**: `#66a556` (Accent green)
- **Tan Light**: `#F7F3E9` (Light tan for backgrounds)
- **Tan Medium**: `#EAE3D2` (Medium tan for card backgrounds)
- **Tan Dark**: `#D3C7A7` (Darker tan for accents)

### Layout Standards
- Content should fill the available space horizontally
- Sidebar width is fixed at 280px
- Main content area should use the remaining space
- Cards should have consistent padding and margins
- Maintain proper spacing between sections

### Typography
- Font family: 'Inter', sans-serif for body text
- Headings should use font-weight of 600
- Text colors should follow the established color system
- Maintain proper hierarchy with consistent heading sizes

## Supabase Integration
- **Auth Flow**: Maintain the hybrid approach with Django shadow users
- **Data Storage**: Keep primary data in Supabase, shadow data in Django
- **API Patterns**: Follow established patterns for Supabase API calls 
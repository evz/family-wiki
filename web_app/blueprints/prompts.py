"""
Prompts management blueprint - simple form-based CRUD operations
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from web_app.services.prompt_service import PromptService


prompts_bp = Blueprint('prompts', __name__, url_prefix='/prompts')

@prompts_bp.route('/')
def list_prompts():
    """List all prompts"""
    prompt_service = PromptService()
    prompts = prompt_service.get_all_prompts()
    active_prompt = prompt_service.get_active_prompt()
    active_prompt_id = active_prompt.id if active_prompt else None

    return render_template('prompts/list.html',
                         prompts=prompts,
                         active_prompt_id=active_prompt_id)

@prompts_bp.route('/create')
def create_prompt():
    """Show create prompt form"""
    return render_template('prompts/edit.html', prompt=None)

@prompts_bp.route('/edit/<prompt_id>')
def edit_prompt(prompt_id):
    """Show edit prompt form"""
    prompt_service = PromptService()
    prompt = prompt_service.get_prompt_by_id(prompt_id)

    if not prompt:
        flash('Prompt not found', 'error')
        return redirect(url_for('prompts.list_prompts'))

    return render_template('prompts/edit.html', prompt=prompt)

@prompts_bp.route('/delete/<prompt_id>')
def delete_prompt(prompt_id):
    """Show delete confirmation form"""
    prompt_service = PromptService()
    prompt = prompt_service.get_prompt_by_id(prompt_id)

    if not prompt:
        flash('Prompt not found', 'error')
        return redirect(url_for('prompts.list_prompts'))

    return render_template('prompts/delete.html', prompt=prompt)

@prompts_bp.route('/save', methods=['POST'])
def save_prompt():
    """Handle create/update prompt form submission"""
    prompt_service = PromptService()

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    prompt_text = request.form.get('prompt_text', '').strip()
    prompt_id = request.form.get('prompt_id')

    # Validate input
    if not name:
        flash('Name is required', 'error')
        if prompt_id:
            return redirect(url_for('prompts.edit_prompt', prompt_id=prompt_id))
        else:
            return redirect(url_for('prompts.create_prompt'))

    if not prompt_text:
        flash('Prompt text is required', 'error')
        if prompt_id:
            return redirect(url_for('prompts.edit_prompt', prompt_id=prompt_id))
        else:
            return redirect(url_for('prompts.create_prompt'))

    if prompt_id:
        # Update existing prompt
        result = prompt_service.update_prompt(prompt_id, name, prompt_text, description)
        if result:
            flash('Prompt updated successfully', 'success')
        else:
            flash('Prompt not found or invalid ID', 'error')
    else:
        # Create new prompt
        prompt_service.create_prompt(name, prompt_text, description)
        flash('Prompt created successfully', 'success')

    return redirect(url_for('prompts.list_prompts'))

@prompts_bp.route('/activate/<prompt_id>', methods=['POST'])
def activate_prompt(prompt_id):
    """Handle activate prompt form submission"""
    prompt_service = PromptService()
    success = prompt_service.set_active_prompt(prompt_id)

    if success:
        flash('Prompt activated successfully', 'success')
    else:
        flash('Failed to activate prompt - prompt not found or invalid ID', 'error')

    return redirect(url_for('prompts.list_prompts'))

@prompts_bp.route('/confirm-delete/<prompt_id>', methods=['POST'])
def confirm_delete_prompt(prompt_id):
    """Handle delete confirmation form submission"""
    prompt_service = PromptService()
    success = prompt_service.delete_prompt(prompt_id)

    if success:
        flash('Prompt deleted successfully', 'success')
    else:
        flash('Failed to delete prompt - cannot delete active prompt or only remaining prompt', 'error')

    return redirect(url_for('prompts.list_prompts'))

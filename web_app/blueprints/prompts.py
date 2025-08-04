"""
Prompts management blueprint - simple form-based CRUD operations
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from web_app.database import db
from web_app.services.prompt_service import PromptService


prompts_bp = Blueprint('prompts', __name__, url_prefix='/prompts')

@prompts_bp.route('/')
def list_prompts():
    """List all prompts grouped by type"""
    prompt_service = PromptService()
    extraction_prompts = prompt_service.get_all_prompts(prompt_type='extraction')
    rag_prompts = prompt_service.get_all_prompts(prompt_type='rag')

    return render_template('prompts/list.html',
                         extraction_prompts=extraction_prompts,
                         rag_prompts=rag_prompts)

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
    prompt_type = request.form.get('prompt_type', 'extraction').strip()
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

    if prompt_type not in ['extraction', 'rag']:
        flash('Invalid prompt type', 'error')
        if prompt_id:
            return redirect(url_for('prompts.edit_prompt', prompt_id=prompt_id))
        else:
            return redirect(url_for('prompts.create_prompt'))

    try:
        if prompt_id:
            # Update existing prompt with transaction management
            with db.session.begin():
                result = prompt_service.update_prompt(prompt_id, name, prompt_text, description)
                if result:
                    flash('Prompt updated successfully', 'success')
                else:
                    flash('Prompt not found or invalid ID', 'error')
        else:
            # Create new prompt with transaction management
            with db.session.begin():
                prompt_service.create_prompt(name, prompt_text, prompt_type, description)
                flash('Prompt created successfully', 'success')
    except Exception:
        flash('An error occurred while saving the prompt', 'error')

    return redirect(url_for('prompts.list_prompts'))


@prompts_bp.route('/confirm-delete/<prompt_id>', methods=['POST'])
def confirm_delete_prompt(prompt_id):
    """Handle delete confirmation form submission"""
    prompt_service = PromptService()

    try:
        # Delete prompt with transaction management
        with db.session.begin():
            success = prompt_service.delete_prompt(prompt_id)
            if success:
                flash('Prompt deleted successfully', 'success')
            else:
                flash('Failed to delete prompt - prompt not found or invalid ID', 'error')
    except Exception:
        flash('An error occurred while deleting the prompt', 'error')

    return redirect(url_for('prompts.list_prompts'))
